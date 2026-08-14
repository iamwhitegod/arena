"""
Completeness Scorer

Scores the quality of premise, claim, and resolution in a ThoughtUnit.

Scores on 0-10 scale:
- Premise clarity: How clear and effective is the setup?
- Claim strength: How strong and impactful is the core insight?
- Resolution closure: How satisfying and complete is the ending?

Combined into overall completeness score (0.0-1.0) = (premise + claim + resolution) / 30
Target: 0.85+ for production quality, with every component at 8.0+
"""

from typing import Dict, List
from .thought_unit import (
    PRODUCTION_COMPLETENESS_THRESHOLD,
    PRODUCTION_COMPONENT_THRESHOLD,
    ThoughtUnit,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class CompletenessScorer:
    """
    Scores ThoughtUnit completeness across three dimensions.

    Scoring criteria:

    1. Premise Clarity (0-10):
       - Does it establish context effectively?
       - Is the setup clear and purposeful?
       - Does it motivate the claim?

    2. Claim Strength (0-10):
       - Is the insight clear and specific?
       - Is it impactful and memorable?
       - Does it deliver value?

    3. Resolution Closure (0-10):
       - Does it complete the thought?
       - Is the ending satisfying?
       - Does it provide proper closure?

    Overall Completeness = (premise + claim + resolution) / 30
    Target: 0.85+ (8.5/10 average) for production quality
    """

    def __init__(self, api_key=None, model: str = "gpt-4o-mini", *, chat=None):
        """
        Initialize completeness scorer

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
            'units_scored': 0,
            'avg_premise_score': 0.0,
            'avg_claim_score': 0.0,
            'avg_resolution_score': 0.0,
            'avg_completeness_score': 0.0
        }
        # Thread lock for thread-safe metrics tracking in parallel processing
        self._metrics_lock = threading.Lock()

    def score(self, thought_unit: ThoughtUnit) -> Dict:
        """
        Score ThoughtUnit completeness.

        Args:
            thought_unit: ThoughtUnit to score

        Returns:
            Scoring dict with:
            {
                'premise_clarity': float,  # 0.0-10.0
                'claim_strength': float,  # 0.0-10.0
                'resolution_closure': float,  # 0.0-10.0
                'completeness_score': float,  # 0.0-1.0
                'meets_production_standard': bool,  # >= 0.85; components >= 8.0
                'reasoning': {
                    'premise': str,
                    'claim': str,
                    'resolution': str
                },
                'suggestions': List[str]  # How to improve
            }
        """
        # Score the thought unit
        try:
            result = self._score_completeness(
                thought_unit.premise_text,
                thought_unit.claim_text,
                thought_unit.resolution_text,
                thought_unit.rhetorical_type.value
            )

            # Update metrics (thread-safe)
            with self._metrics_lock:
                self.metrics['units_scored'] += 1
                self.metrics['avg_premise_score'] = (
                    (self.metrics['avg_premise_score'] * (self.metrics['units_scored'] - 1) + result['premise_clarity'])
                    / self.metrics['units_scored']
                )
                self.metrics['avg_claim_score'] = (
                    (self.metrics['avg_claim_score'] * (self.metrics['units_scored'] - 1) + result['claim_strength'])
                    / self.metrics['units_scored']
                )
                self.metrics['avg_resolution_score'] = (
                    (self.metrics['avg_resolution_score'] * (self.metrics['units_scored'] - 1) + result['resolution_closure'])
                    / self.metrics['units_scored']
                )
                self.metrics['avg_completeness_score'] = (
                    (self.metrics['avg_completeness_score'] * (self.metrics['units_scored'] - 1) + result['completeness_score'])
                    / self.metrics['units_scored']
                )

            return result

        except Exception as e:
            print(f"      ⚠️  Error scoring completeness: {e}")
            # Return conservative default scores
            return {
                'premise_clarity': 5.0,
                'claim_strength': 5.0,
                'resolution_closure': 5.0,
                'completeness_score': 0.5,
                'meets_production_standard': False,
                'reasoning': {
                    'premise': f'Error during scoring: {e}',
                    'claim': f'Error during scoring: {e}',
                    'resolution': f'Error during scoring: {e}'
                },
                'suggestions': ['Scoring error occurred']
            }

    def _score_completeness(
        self,
        premise_text: str,
        claim_text: str,
        resolution_text: str,
        rhetorical_type: str
    ) -> Dict:
        """
        Use GPT to score completeness.

        Args:
            premise_text: Premise text
            claim_text: Claim text
            resolution_text: Resolution text
            rhetorical_type: Type of rhetoric

        Returns:
            Scoring dict
        """
        # Create prompt
        prompt = self._create_scoring_prompt(
            premise_text,
            claim_text,
            resolution_text,
            rhetorical_type
        )

        # Call with retry for rate limits
        from arena.providers.base import ResponseMode
        from arena.providers.retry import retry_with_backoff

        response = retry_with_backoff(
            lambda: self._chat.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video editor and content analyst who scores the completeness and quality of video clips on a precise 0-10 scale."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
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

            premise_score = float(result.get('premise_clarity', 5.0))
            claim_score = float(result.get('claim_strength', 5.0))
            resolution_score = float(result.get('resolution_closure', 5.0))

            # Calculate completeness score
            completeness_score = (premise_score + claim_score + resolution_score) / 30.0

            # Check if meets production standard
            # Keep this result aligned with ThoughtUnit.meets_production_standard().
            meets_production = (
                completeness_score >= PRODUCTION_COMPLETENESS_THRESHOLD and
                premise_score >= PRODUCTION_COMPONENT_THRESHOLD and
                claim_score >= PRODUCTION_COMPONENT_THRESHOLD and
                resolution_score >= PRODUCTION_COMPONENT_THRESHOLD
            )

            return {
                'premise_clarity': premise_score,
                'claim_strength': claim_score,
                'resolution_closure': resolution_score,
                'completeness_score': completeness_score,
                'meets_production_standard': meets_production,
                'reasoning': result.get('reasoning', {}),
                'suggestions': result.get('suggestions', [])
            }

        except (KeyError, ValueError) as e:
            print(f"      ⚠️  Failed to parse scoring response: {e}")
            return {
                'premise_clarity': 5.0,
                'claim_strength': 5.0,
                'resolution_closure': 5.0,
                'completeness_score': 0.5,
                'meets_production_standard': False,
                'reasoning': {'error': f'Parse error: {e}'},
                'suggestions': []
            }

    def _create_scoring_prompt(
        self,
        premise_text: str,
        claim_text: str,
        resolution_text: str,
        rhetorical_type: str
    ) -> str:
        """
        Create prompt for completeness scoring.

        Args:
            premise_text: Premise text
            claim_text: Claim text
            resolution_text: Resolution text
            rhetorical_type: Type of rhetoric

        Returns:
            Prompt string
        """
        return f"""You are scoring a video clip for completeness and quality.

CLIP STRUCTURE:

PREMISE (Setup/Context):
"{premise_text}"

CLAIM (Core Insight):
"{claim_text}"

RESOLUTION (Closure):
"{resolution_text}"

RHETORICAL TYPE: {rhetorical_type}

---

TASK: Score each component on a 0-10 scale.

## 1. PREMISE CLARITY (0-10)

Rate how effectively the premise sets up the claim:

**10 = Perfect Setup**
- Crystal clear context
- Naturally motivates the claim
- Hooks attention immediately
- No confusion about topic

**8-9 = Strong Setup**
- Clear context
- Good motivation
- Minor room for improvement

**6-7 = Adequate Setup**
- Gets the job done
- Some clarity issues
- Could be stronger

**4-5 = Weak Setup**
- Unclear or confusing
- Poor motivation
- Lacks direction

**0-3 = Failed Setup**
- Confusing or missing
- Doesn't support claim
- Viewer is lost

## 2. CLAIM STRENGTH (0-10)

Rate the power and clarity of the core insight:

**10 = Exceptional Claim**
- Crystal clear insight
- Highly impactful
- Memorable and quotable
- Delivers strong value

**8-9 = Strong Claim**
- Clear and impactful
- Good value delivery
- Minor refinement possible

**6-7 = Adequate Claim**
- Gets point across
- Decent value
- Could be sharper

**4-5 = Weak Claim**
- Unclear or vague
- Low impact
- Limited value

**0-3 = Failed Claim**
- Confusing or missing
- No clear insight
- No value delivered

## 3. RESOLUTION CLOSURE (0-10)

Rate how satisfyingly the thought completes:

**10 = Perfect Closure**
- Complete and satisfying ending
- No loose threads
- Natural stopping point
- Exceptional quality

**8-9 = Strong Closure**
- Clear ending with good closure
- Viewer feels satisfied
- Good sense of completion
- Publishable quality

**7 = Good Closure** (Acceptable for production)
- Thought completes properly
- Natural ending point
- Viewer understands the point
- No major confusion

**6 = Adequate Closure**
- Gets to an ending
- Some minor loose threads but acceptable
- Could be slightly better but usable

**4-5 = Weak Closure**
- Unclear or abrupt ending
- Viewer somewhat confused
- Needs improvement

**0-3 = Failed Closure**
- No real ending
- Mid-thought cutoff
- Not usable

---

SCORING CONTEXT:

**Exceptional Quality = 8.5+ average (all three >= 8.0)**
- Outstanding clips that need no editing
- 95%+ viewers satisfied
- Premium content quality

**Production Quality = 6.0-8.4 average (most >= 5.5)** ← TARGET BAR
- "Publish as-is" standard
- 70-90% viewers satisfied
- Ready for social media distribution
- This is the realistic production bar

**Acceptable Quality = 5.0-5.9 average**
- Good enough for most uses
- Minor polish would help but not required
- Still usable

**Needs Work = 3.5-4.9 average**
- Some issues
- May require editing before publishing

**Not Usable = <3.5 average**
- Major problems
- Should not be published

IMPORTANT: Be realistic and generous. A 6.0 resolution that completes the thought properly
should score 6.0, not 4.0. Reserve low scores (3-4) for truly problematic content.
Most clips from real-world content will score in the 5.5-8.0 range.

---

RETURN JSON:
{{
  "premise_clarity": <0.0-10.0>,
  "claim_strength": <0.0-10.0>,
  "resolution_closure": <0.0-10.0>,
  "reasoning": {{
    "premise": "Why this score for premise...",
    "claim": "Why this score for claim...",
    "resolution": "Why this score for resolution..."
  }},
  "suggestions": [
    "How to improve premise...",
    "How to strengthen claim...",
    "How to enhance resolution..."
  ]
}}

Be honest and precise. A score of 8.0+ means truly production-ready.
Most clips will score 6-8 range. Reserve 9-10 for exceptional quality.
"""

    def score_batch(
        self,
        thought_units: List[ThoughtUnit],
        verbose: bool = True
    ) -> List[Dict]:
        """
        Score multiple ThoughtUnits.

        Args:
            thought_units: List of ThoughtUnit instances
            verbose: Print progress

        Returns:
            List of scoring dicts
        """
        scores = []

        for idx, unit in enumerate(thought_units, 1):
            if verbose:
                print(f"      Scoring completeness {idx}/{len(thought_units)} ({unit.duration:.1f}s, {unit.rhetorical_type.value})...")

            score_result = self.score(unit)

            if verbose:
                completeness = score_result['completeness_score']
                production_str = "✓ PRODUCTION" if score_result['meets_production_standard'] else "⚠ NEEDS WORK"
                print(f"      {production_str} (score: {completeness:.2f})")
                print(f"        Premise: {score_result['premise_clarity']:.1f} | Claim: {score_result['claim_strength']:.1f} | Resolution: {score_result['resolution_closure']:.1f}")

            scores.append(score_result)

        if verbose:
            production_rate = sum(1 for s in scores if s['meets_production_standard']) / len(thought_units) * 100 if thought_units else 0
            avg_score = self.metrics['avg_completeness_score']
            print(f"      Completeness scoring: {sum(1 for s in scores if s['meets_production_standard'])}/{len(thought_units)} meet production standard ({production_rate:.0f}%)")
            print(f"      Average completeness: {avg_score:.2f}")

        return scores

    def score_batch_parallel(
        self,
        thought_units: List[ThoughtUnit],
        max_workers: int = 5,
        verbose: bool = True
    ) -> List[Dict]:
        """
        Score multiple ThoughtUnits in parallel (FASTER).

        This method uses ThreadPoolExecutor to score multiple units concurrently,
        providing 3-5x speedup compared to score_batch() for large batches.

        Args:
            thought_units: List of ThoughtUnit instances
            max_workers: Maximum parallel API calls (default: 5)
                        Higher = faster but more API pressure
                        Recommended: 5-10
            verbose: Print progress

        Returns:
            List of scoring dicts (in same order as input)

        Performance:
            Sequential (score_batch):   10 units × 2s = 20s
            Parallel (5 workers):       10 units / 5 × 2s = 4s  (5x faster)

        Thread-safety:
            Uses threading.Lock for metrics tracking to ensure accuracy.
        """
        if not thought_units:
            return []

        # Pre-allocate results list to maintain order
        scores = [None] * len(thought_units)

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scoring tasks
            future_to_index = {
                executor.submit(self.score, unit): idx
                for idx, unit in enumerate(thought_units)
            }

            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                idx = future_to_index[future]

                try:
                    result = future.result()
                    scores[idx] = result

                    completed += 1
                    if verbose:
                        unit = thought_units[idx]
                        completeness = result['completeness_score']
                        production_str = "✓ PRODUCTION" if result['meets_production_standard'] else "⚠ NEEDS WORK"
                        print(f"      [{completed}/{len(thought_units)}] {production_str} (score: {completeness:.2f}, {unit.duration:.1f}s)")

                except Exception as e:
                    print(f"      ⚠️  Error scoring unit {idx+1}: {e}")
                    # Use conservative default scores on error
                    scores[idx] = {
                        'premise_clarity': 5.0,
                        'claim_strength': 5.0,
                        'resolution_closure': 5.0,
                        'completeness_score': 0.5,
                        'meets_production_standard': False,
                        'reasoning': {'error': f'Scoring error: {e}'},
                        'suggestions': []
                    }

        # Print summary
        if verbose:
            production_count = sum(1 for s in scores if s and s['meets_production_standard'])
            production_rate = (production_count / len(scores) * 100) if scores else 0
            avg_score = self.metrics['avg_completeness_score']
            print(f"      Completeness scoring: {production_count}/{len(scores)} meet production standard ({production_rate:.0f}%)")
            print(f"      Average completeness: {avg_score:.2f}")

        return scores

    def update_thought_units(
        self,
        thought_units: List[ThoughtUnit],
        scores: List[Dict]
    ) -> List[ThoughtUnit]:
        """
        Update ThoughtUnits with scoring results.

        Args:
            thought_units: Original ThoughtUnit instances
            scores: Scoring results

        Returns:
            Updated ThoughtUnit instances with new scores
        """
        updated_units = []

        for unit, score_result in zip(thought_units, scores):
            # Update scores
            unit.premise_clarity = score_result['premise_clarity']
            unit.claim_strength = score_result['claim_strength']
            unit.resolution_closure = score_result['resolution_closure']
            unit.completeness_score = score_result['completeness_score']

            # Store scoring metadata
            unit._detection_metadata.update({
                'scoring_reasoning': score_result['reasoning'],
                'scoring_suggestions': score_result['suggestions'],
                'meets_production_standard': score_result['meets_production_standard']
            })

            updated_units.append(unit)

        return updated_units
