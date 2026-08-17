"""
Standalone Context Validator

Validates that a ThoughtUnit is standalone (understandable without prior context).

Checks for:
- Unresolved pronouns (he, she, it, they without clear antecedents)
- Demonstrative references (this, that, these without clear referents)
- Incomplete comparisons ("better than..." without the comparison target)
- Assumed context ("that's why..." without establishing "why")

This ensures clips work on social media where viewers have no prior context.
"""

from typing import Dict, List
from .thought_unit import (
    ThoughtUnit,
    DependencyLevel,
    safe_float,
    safe_string_list,
    safe_text,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class StandaloneValidator:
    """
    Validates that ThoughtUnits are standalone (contextually independent).

    A standalone clip must:
    1. Have no unresolved pronouns (he/she/it/they with unclear antecedents)
    2. Have no dangling demonstratives (this/that without clear referents)
    3. Have no incomplete comparisons (better than... what?)
    4. Have no assumed prior context (that's why... why what?)

    Strategy:
    - Use GPT-4o-mini to analyze the full text
    - Detect unresolved references
    - Calculate standalone score (0.0-1.0)
    - Mark units as STANDALONE or NEEDS_CONTEXT
    """

    def __init__(self, api_key=None, model: str = "gpt-4o-mini", *, chat=None):
        """
        Initialize standalone validator

        Args:
            api_key: OpenAI API key (legacy, creates OpenAIChatModel internally)
            model: Model to use (default: gpt-4o-mini)
            chat: ChatModel inference port (preferred)
        """
        if chat is not None:
            self._chat = chat
        elif api_key is not None:
            from arena.providers.openai_adapter import OpenAIChatModel
            self._chat = OpenAIChatModel(api_key=api_key, model=model)
        else:
            raise ValueError("Either chat or api_key required")
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'units_validated': 0,
            'units_standalone': 0,
            'units_need_context': 0,
            'units_unsalvageable': 0
        }
        # Thread lock for thread-safe metrics tracking in parallel processing
        self._metrics_lock = threading.Lock()

    def validate(self, thought_unit: ThoughtUnit) -> Dict:
        """
        Validate if ThoughtUnit is standalone.

        Args:
            thought_unit: ThoughtUnit to validate

        Returns:
            Validation dict with:
            {
                'is_standalone': bool,
                'dependency_level': DependencyLevel,
                'standalone_score': float,  # 0.0-1.0
                'issues': List[str],  # List of problems found
                'unresolved_refs': List[str],  # Specific unresolved references
                'reasoning': str,  # Why this is/isn't standalone
                'confidence': float  # Detection confidence
            }
        """
        # Analyze the full text
        full_text = thought_unit.full_text

        # Call GPT to analyze standalone context
        try:
            result = self._analyze_standalone(full_text, thought_unit.rhetorical_type.value)

            # Update metrics (thread-safe)
            with self._metrics_lock:
                self.metrics['units_validated'] += 1

                if result['is_standalone']:
                    self.metrics['units_standalone'] += 1
                elif result['dependency_level'] == 'needs_context':
                    self.metrics['units_need_context'] += 1
                else:
                    self.metrics['units_unsalvageable'] += 1

            return result

        except Exception as e:
            print(f"      ⚠️  Error validating standalone: {e}")
            # Return conservative default (assume needs context)
            return {
                'is_standalone': False,
                'dependency_level': DependencyLevel.NEEDS_CONTEXT,
                'standalone_score': 0.5,
                'issues': ['Validation error'],
                'unresolved_refs': [],
                'reasoning': f'Error during validation: {e}',
                'confidence': 0.0
            }

    def _analyze_standalone(
        self,
        text: str,
        rhetorical_type: str
    ) -> Dict:
        """
        Use GPT to analyze standalone context.

        Args:
            text: Full text of the thought unit
            rhetorical_type: Type of rhetoric

        Returns:
            Validation dict
        """
        # Create prompt
        prompt = self._create_standalone_prompt(text, rhetorical_type)

        # Call with retry for rate limits
        from arena.providers.base import ResponseMode
        from arena.providers.retry import retry_with_backoff

        response = retry_with_backoff(
            lambda: self._chat.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing text for standalone comprehension. You identify unresolved references that break understanding for readers without prior context."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_mode=ResponseMode.JSON,
            )
        )

        # Track metrics (thread-safe)
        with self._metrics_lock:
            self.metrics['api_calls'] += 1
            self.metrics['tokens_used'] += response.usage.total_tokens
            if response.usage.estimated_cost_usd is not None:
                self.metrics['cost_usd'] += float(response.usage.estimated_cost_usd)

        # Parse response
        try:
            result = response.parsed
            if not isinstance(result, dict):
                raise TypeError("Standalone response must be an object")

            # Map to dependency level
            dependency_level_str = result.get('dependency_level', 'needs_context')
            if not isinstance(dependency_level_str, str):
                dependency_level_str = 'needs_context'
            dependency_level = self._map_dependency_level(dependency_level_str)
            standalone_score = safe_float(result.get('standalone_score'), 0.5)
            reported_standalone = result.get('is_standalone')
            is_standalone = (
                reported_standalone is True
                and dependency_level == DependencyLevel.STANDALONE
                and standalone_score >= 0.55
            )

            return {
                'is_standalone': is_standalone,
                'dependency_level': dependency_level,
                'standalone_score': standalone_score,
                'issues': safe_string_list(result.get('issues')),
                'unresolved_refs': safe_string_list(result.get('unresolved_refs')),
                'reasoning': safe_text(result.get('reasoning')),
                'confidence': safe_float(result.get('confidence'), 0.5),
            }

        except (KeyError, TypeError):
            print("      ⚠️  Failed to parse standalone response")
            return {
                'is_standalone': False,
                'dependency_level': DependencyLevel.NEEDS_CONTEXT,
                'standalone_score': 0.5,
                'issues': ['Parse error'],
                'unresolved_refs': [],
                'reasoning': 'Parse error',
                'confidence': 0.0
            }

    def _create_standalone_prompt(self, text: str, rhetorical_type: str) -> str:
        """
        Create prompt for standalone analysis.

        Args:
            text: Full text to analyze
            rhetorical_type: Type of rhetoric

        Returns:
            Prompt string
        """
        return f"""You are analyzing a clip to determine if it is STANDALONE FOR ITS INTENDED AUDIENCE.

CLIP TEXT:
"{text}"

RHETORICAL TYPE: {rhetorical_type}

⚠️ AUDIENCE-RELATIVE STANDALONE CONTEXT (ARSC):

A clip is standalone if it is COMPLETE FOR ITS INTENDED AUDIENCE, even if it relies on:
- Shared beliefs or domain knowledge
- Personal authority ("I've seen", "In my experience", "From the Bible")
- Cultural context the audience already has

The intended audience is DOMAIN-NATIVE and accepts implicit references.

For this content:
- Personal testimony is valid standalone context
- Phrases like "what I've seen", "in my experience", "from the Bible", "in scripture"
  do NOT require explicit examples or verse citations
- Shared domain knowledge (biblical, tech, business) is acceptable
- Do NOT require exhaustive explanation if the idea is already complete for the target audience

❌ ONLY reject a clip if:
- The core idea itself is missing
- The claim cannot be understood even by a domain-aware listener
- Critical information is completely absent (not just implicit)

✅ ASK: "Would the INTENDED AUDIENCE feel this clip is complete?"
❌ NOT: "Would a random person with zero domain knowledge fully understand this?"

⚠️ CRITICAL - CONTENT-AWARE VALIDATION RULES:

🔍 BEFORE FLAGGING A PRONOUN AS "UNRESOLVED", CHECK:
1. Is the antecedent mentioned in the SAME CLIP? → ✅ NOT UNRESOLVED
2. Is it generic "you" meaning "anyone"? → ✅ NOT UNRESOLVED
3. Does it refer to a known entity (God, Jesus, etc.)? → ✅ NOT UNRESOLVED

DO NOT flag these as "unresolved references":
- ✅ God, Jesus, Holy Spirit, biblical figures (Moses, Paul, David, etc.) - THESE ARE KNOWN
- ✅ Pronouns with clear antecedents IN THE SAME CLIP (read the full text!)
- ✅ Generic "you" (means "anyone" - always clear)
- ✅ Well-known public figures (presidents, celebrities, historical figures)
- ✅ Common tech terms and frameworks in tech content
- ✅ Industry-specific terms in business content

ONLY flag TRULY AMBIGUOUS pronouns:
- ❌ "he/she/it/they" referring to people NOT mentioned anywhere in this clip
- ❌ "This person" without any identifying information
- ❌ References to unnamed individuals from earlier parts of the video (NOT in this clip)

TASK:
Analyze if this clip can be understood by someone who has NO prior context.

CHECK FOR THESE ISSUES:

1. **Unresolved Pronouns**:
   ⚠️ CRITICAL: Pronouns are OK if the antecedent is clear!

   ✅ ACCEPTABLE PRONOUNS:
   - Generic "you" (means "anyone", "people in general") - ALWAYS OK
   - "he/she/it" when antecedent is in the SAME CLIP (look back in the text!)
   - Example: "God wants us to pray. He hears our prayers." (✅ "He" = God, CLEAR)
   - Example: "When God speaks, he knows what we need." (✅ "he" = God, CLEAR)
   - Example: "You should pray daily." (✅ generic "you", CLEAR)

   ❌ ONLY FLAG AS UNRESOLVED:
   - "he/she/it/they" referring to people NOT mentioned in this clip
   - Example: "That's why he said we should pray" (❌ who is "he"? Not mentioned!)
   - Example: "After she left, I realized..." (❌ who is "she"? Unknown!)

   🔍 HOW TO CHECK:
   - Read the FULL clip text carefully
   - If pronoun appears, look for its antecedent in the SAME CLIP
   - If antecedent is found = ✅ OK, NOT unresolved
   - If antecedent NOT in clip = ❌ Flag as unresolved

2. **Demonstrative References**:
   - "this", "that", "these", "those" pointing to unknown things
   - Example: "That's the problem" (what problem? - needs definition)
   - Example: "This is why..." (why what? - needs context)
   - ✅ OK if thing is defined: "This principle..."
   - ✅ OK if reference is to common knowledge within the content domain

3. **Incomplete Comparisons**:
   - "better than...", "worse than...", "more than..." without target
   - Example: "It's better than that" (better than what?)
   - OK if comparison is complete: "better than wealth"

4. **Assumed Prior Context**:
   - "So that's why...", "As I said...", "Remember when..."
   - Assumes viewer knows previous information
   - OK if context is established within the clip

5. **Mid-Conversation References**:
   - "Back to what I was saying..."
   - "Like I mentioned earlier..."
   - OK if it refers to something said IN THIS CLIP

IMPORTANT - CONTENT-AWARE VALIDATION:
- Religious content: God, Jesus, biblical figures are KNOWN (not unresolved)
- Tech content: Common tech terms, frameworks are KNOWN
- Business content: Industry terms are KNOWN
- General knowledge figures (presidents, celebrities) are KNOWN
- Only flag TRULY ambiguous references (unnamed "he/she/it/they")

STANDALONE SCORING (Audience-Relative):
- 1.0 = Perfect (zero issues for target audience)
- 0.8-0.9 = Excellent (complete for domain-aware viewers)
- 0.7 = Good (target audience easily understands the main point)
- 0.55-0.69 = Acceptable with minor gaps (message still clear to audience)
- 0.3-0.54 = Poor (even domain-aware listeners confused)
- 0.0-0.29 = Unsalvageable (completely depends on prior context)

⚠️ CRITICAL SCORING RULES (ARSC):
- Personal testimony/authority ("I've seen", "In my experience") → Score 0.7+
- Domain references without citations ("the Bible says", "in scripture") → Score 0.7+
- Pronouns with clear antecedents in the clip → Score 0.8+
- Generic "you" → Score 0.9+
- ONLY score below 0.55 if the INTENDED AUDIENCE can't understand the core claim

DEPENDENCY LEVELS:
- "standalone" = Score 0.55+ (complete for intended audience, publishable)
- "needs_context" = Score 0.3-0.54 (even target audience confused)
- "unsalvageable" = Score <0.3 (completely incomprehensible)

RETURN JSON:
{{
  "is_standalone": <true|false>,
  "standalone_score": <0.0-1.0>,
  "dependency_level": "standalone|needs_context|unsalvageable",
  "issues": ["List of specific issues found"],
  "unresolved_refs": ["Specific words/phrases that are unresolved"],
  "reasoning": "Why this is/isn't standalone",
  "confidence": <0.0-1.0>
}}

CONTRASTIVE EXAMPLES (Critical for Calibration):

✅ VALID STANDALONE (score 0.8+):
"What I've seen in the Bible is that obedience often precedes clarity."

Reasoning:
- The claim is complete for the intended audience
- Biblical reference establishes personal authority (acceptable for domain)
- No additional setup is required for a sermon audience
- The CORE IDEA ("obedience → clarity") is fully present
→ ✅ DO NOT penalize for lack of verse citations

✅ VALID STANDALONE (score 0.9+):
"God did not force anyone to accept him even though he wants everyone to be his wife."

Reasoning:
- "God" is domain-known entity
- "him" and "he" clearly refer to God (antecedent in same sentence)
- Generic "anyone" and "everyone" are clear
- Intended audience fully understands this claim
→ ✅ Pronouns with clear antecedents are NOT unresolved

✅ VALID STANDALONE (score 0.8+):
"In my experience building startups, the hardest part is finding product-market fit."

Reasoning:
- Personal authority is valid for creator content
- "In my experience" establishes context
- Audience accepts implicit references
- Core claim is complete
→ ✅ DO NOT require exhaustive explanation

❌ INVALID STANDALONE (score 0.4):
"And that's why obedience matters more than we think."

Reasoning:
- Missing setup: "that's why" refers to something not in clip
- The claim depends on earlier explanation
- Even domain-aware audience can't understand the reasoning
- Core idea is incomplete
→ ❌ This genuinely needs context

❌ INVALID STANDALONE (score 0.3):
"So going back to what I said earlier, that's exactly what he meant."

Reasoning:
- Multiple unresolved: "what I said", "he" (no antecedent), "that"
- Core claim is missing
- Even domain audience can't reconstruct the argument
→ ❌ Unsalvageable without context
"""

    def _map_dependency_level(self, level_str: str) -> DependencyLevel:
        """
        Map string to DependencyLevel enum.

        Args:
            level_str: String like 'standalone', 'needs_context', 'unsalvageable'

        Returns:
            DependencyLevel enum
        """
        mapping = {
            'standalone': DependencyLevel.STANDALONE,
            'needs_context': DependencyLevel.NEEDS_CONTEXT,
            'unsalvageable': DependencyLevel.UNSALVAGEABLE
        }
        return mapping.get(level_str.lower(), DependencyLevel.NEEDS_CONTEXT)

    def validate_batch(
        self,
        thought_units: List[ThoughtUnit],
        verbose: bool = True
    ) -> List[Dict]:
        """
        Validate multiple ThoughtUnits.

        Args:
            thought_units: List of ThoughtUnit instances
            verbose: Print progress

        Returns:
            List of validation dicts
        """
        validations = []

        for idx, unit in enumerate(thought_units, 1):
            if verbose:
                print(f"      Validating standalone {idx}/{len(thought_units)} ({unit.duration:.1f}s, {unit.rhetorical_type.value})...")

            validation = self.validate(unit)

            if verbose:
                standalone_str = "✓ STANDALONE" if validation['is_standalone'] else "✗ NEEDS CONTEXT"
                score_str = f"{validation['standalone_score']:.2f}"
                print(f"      {standalone_str} (score: {score_str})")

                if validation['issues']:
                    for issue in validation['issues'][:2]:  # Show first 2 issues
                        print(f"        - {issue}")

            validations.append(validation)

        if verbose:
            standalone_rate = self.metrics['units_standalone'] / len(thought_units) * 100 if thought_units else 0
            print(f"      Standalone validation: {self.metrics['units_standalone']}/{len(thought_units)} ({standalone_rate:.0f}%)")

        return validations

    def validate_batch_parallel(
        self,
        thought_units: List[ThoughtUnit],
        max_workers: int = 5,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Validate multiple ThoughtUnits in parallel (FASTER).

        This method uses ThreadPoolExecutor to validate multiple units concurrently,
        providing 3-5x speedup compared to validate_batch() for large batches.

        Args:
            thought_units: List of ThoughtUnit instances
            max_workers: Maximum parallel API calls (default: 5)
                        Higher = faster but more API pressure
                        Recommended: 5-10
            verbose: Print progress

        Returns:
            List of validation dicts (in same order as input)

        Performance:
            Sequential (validate_batch): 10 units × 1.5s = 15s
            Parallel (5 workers):        10 units / 5 × 1.5s = 3s  (5x faster)

        Thread-safety:
            Uses threading.Lock for metrics tracking to ensure accuracy.
        """
        if not thought_units:
            return []

        # Pre-allocate results list to maintain order
        validations = [None] * len(thought_units)

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all validation tasks
            future_to_index = {
                executor.submit(self.validate, unit): idx
                for idx, unit in enumerate(thought_units)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]

                try:
                    result = future.result()
                    validations[idx] = result

                    completed += 1
                    if verbose:
                        unit = thought_units[idx]
                        standalone_str = "✓ STANDALONE" if result['is_standalone'] else "✗ NEEDS CONTEXT"
                        score_str = f"{result['standalone_score']:.2f}"
                        print(f"      [{completed}/{len(thought_units)}] {standalone_str} (score: {score_str}, {unit.duration:.1f}s)")

                        # Show first issue if any
                        if result['issues'] and len(result['issues']) > 0:
                            print(f"        - {result['issues'][0]}")

                except Exception as e:
                    print(f"      ⚠️  Error validating unit {idx+1}: {e}")
                    # Use conservative default on error
                    validations[idx] = {
                        'is_standalone': False,
                        'dependency_level': DependencyLevel.NEEDS_CONTEXT,
                        'standalone_score': 0.5,
                        'issues': ['Validation error'],
                        'unresolved_refs': [],
                        'reasoning': f'Error during validation: {e}',
                        'confidence': 0.0
                    }

        # Print summary
        if verbose:
            standalone_count = sum(1 for v in validations if v and v['is_standalone'])
            standalone_rate = (standalone_count / len(validations) * 100) if validations else 0
            print(f"      Standalone validation: {standalone_count}/{len(validations)} ({standalone_rate:.0f}%)")

        return validations

    def update_thought_units(
        self,
        thought_units: List[ThoughtUnit],
        validations: List[Dict]
    ) -> List[ThoughtUnit]:
        """
        Update ThoughtUnits with validation results.

        Args:
            thought_units: Original ThoughtUnit instances
            validations: Validation results

        Returns:
            Updated ThoughtUnit instances with new dependency_level and has_unresolved_refs
        """
        updated_units = []

        for unit, validation in zip(thought_units, validations):
            # Update dependency level
            unit.dependency_level = validation['dependency_level']

            # Update unresolved refs flag
            unit.has_unresolved_refs = not validation['is_standalone']

            # Store validation metadata
            unit._detection_metadata.update({
                'standalone_score': validation['standalone_score'],
                'standalone_issues': validation['issues'],
                'unresolved_refs': validation['unresolved_refs'],
                'standalone_reasoning': validation['reasoning']
            })

            # Recalculate completeness score with updated flags
            unit.completeness_score = unit.calculate_completeness_score()

            updated_units.append(unit)

        return updated_units
