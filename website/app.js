/* ==========================================================================
   Arena Landing Page - Interactive Controller & Simulations
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initMobileMenu();
  initClipboardCopy();
  initPlatformCropShowcase();
  initScrollReveals();
  initFaqAccordion();
  
  // Start the live CLI simulation
  startCliSimulation();
});

/* ==========================================================================
   1. Mobile Navigation Menu
   ========================================================================== */
function initMobileMenu() {
  const toggle = document.getElementById('menu-toggle');
  const links = document.querySelector('.nav-links');
  
  if (toggle && links) {
    toggle.addEventListener('click', () => {
      links.classList.toggle('active');
      toggle.classList.toggle('active');
    });
    
    // Close mobile menu on nav link click
    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        links.classList.remove('active');
        toggle.classList.remove('active');
      });
    });
  }
}

/* ==========================================================================
   2. Clipboard Copy & Toast Confirmation
   ========================================================================== */
function initClipboardCopy() {
  const copyButtons = document.querySelectorAll('.btn-copy');
  const toast = document.getElementById('toast-notification');
  
  copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const targetEl = document.getElementById(targetId);
      
      if (targetEl) {
        const textToCopy = targetEl.textContent || targetEl.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
          // Trigger sleek toast notification
          if (toast) {
            toast.classList.add('visible');
            setTimeout(() => {
              toast.classList.remove('visible');
            }, 2000);
          }
        }).catch(err => {
          console.error('Failed to copy text: ', err);
        });
      }
    });
  });
}

/* ==========================================================================
   3. Interactive Platform Crop Showcase
   ========================================================================== */
const cropPresets = {
  tiktok: {
    title: 'TikTok / YouTube Shorts (9:16 Vertical)',
    ratioText: 'TikTok (9:16 Crop)',
    class: 'aspect-tiktok',
    command: 'arena format clips/ -p tiktok --crop smart --pad blur',
    desc: 'Applies an advanced center-subject tracking crop. Automatically pads the vertical boundaries (top and bottom) with a stylized, real-time Gaussian-blurred expansion of the source frame, making horizontal podcast interviews look premium and highly engaging on vertical feeds.'
  },
  square: {
    title: 'Instagram Feed / LinkedIn Post (1:1 Square)',
    ratioText: 'Instagram (1:1 Feed)',
    class: 'aspect-square',
    command: 'arena format clips/ -p instagram-feed --crop center',
    desc: 'Crops the video into a 1:1 box with centered framing. This preset is perfect for LinkedIn, Twitter/X, and classic Instagram feeds where square formats cover more screen real-estate without requiring vertical crops.'
  },
  youtube: {
    title: 'YouTube / Desktop Web (16:9 Landscape)',
    ratioText: 'YouTube (16:9 Landscape)',
    class: 'aspect-youtube',
    command: 'arena format clips/ -p youtube -o desktop/',
    desc: 'Keeps the standard cinematic 16:9 widescreen orientation. Rather than altering aspect ratios, the engine extracts the selected highlight segments in high-quality lossless form, ready for YouTube, newsletters, or online courses.'
  }
};

function initPlatformCropShowcase() {
  const buttons = document.querySelectorAll('.crop-btn');
  const frame = document.getElementById('preview-frame');
  const ratioText = document.getElementById('preview-ratio-text');
  const metaTitle = document.getElementById('crop-meta-title');
  const metaDesc = document.getElementById('crop-meta-desc');
  const codeBadge = document.querySelector('.crop-flags-badge code');
  
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      // Manage active button class
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      const presetName = btn.getAttribute('data-ratio');
      const preset = cropPresets[presetName];
      
      if (preset && frame) {
        // Clear old aspect classes and apply new one
        frame.className = 'crop-preview-frame';
        frame.classList.add(preset.class);
        
        // Update content previews
        if (ratioText) ratioText.textContent = preset.ratioText;
        if (metaTitle) metaTitle.textContent = preset.title;
        if (metaDesc) metaDesc.textContent = preset.desc;
        if (codeBadge) codeBadge.textContent = preset.command;
      }
    });
  });
}

/* ==========================================================================
   4. Scroll Entry Reveals (IntersectionObserver Fallback)
   ========================================================================== */
function initScrollReveals() {
  const elements = document.querySelectorAll('.scroll-reveal');
  
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          // Once revealed, we don't need to observe it anymore
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });
    
    elements.forEach(el => observer.observe(el));
  } else {
    // Fallback if IntersectionObserver is not supported
    elements.forEach(el => el.classList.add('revealed'));
  }
}

/* ==========================================================================
   5. Interactive CLI & Pipeline Simulation
   ========================================================================== */
const mockClipsData = [
  {
    num: '001',
    title: 'Fascinated by Power &amp; Politics',
    time: '00:00 → 00:34',
    duration: '34s',
    aiScore: '0.92',
    hybridScore: '0.92',
    desc: 'A powerful clip breaking down high-stakes politics and public systems with clean framing.',
    topic: 'Governance'
  },
  {
    num: '002',
    title: 'The Art of Therapy and Human Mind',
    time: '00:51 → 01:35',
    duration: '44s',
    aiScore: '0.90',
    hybridScore: '0.90',
    desc: 'Explores standard cognitive therapies and visual representations of standard mental models.',
    topic: 'Psychology'
  },
  {
    num: '003',
    title: 'From Depression to Recovery',
    time: '02:00 → 02:39',
    duration: '39s',
    aiScore: '0.88',
    hybridScore: '0.88',
    desc: 'A moving clip discussing recovery methods, mindfulness, and visual pacing boundaries.',
    topic: 'Health'
  },
  {
    num: '004',
    title: 'Navigating Trauma and Purpose',
    time: '02:58 → 03:47',
    duration: '49s',
    aiScore: '0.86',
    hybridScore: '0.86',
    desc: 'Focuses on the challenges of early twenties and building strong mental resilience.',
    topic: 'Growth'
  }
];

let simTimeoutIds = [];
let currentCommandIndex = 0;

function clearAllSimTimeouts() {
  simTimeoutIds.forEach(id => {
    clearTimeout(id);
    clearInterval(id);
  });
  simTimeoutIds = [];
}

function scheduleSimTimeout(fn, ms) {
  const id = setTimeout(fn, ms);
  simTimeoutIds.push(id);
  return id;
}

const commandsSequence = [
  {
    cmdText: 'arena init',
    terminalTitle: 'bash — arena init',
    run: (addLine, addProgressLine, onComplete) => {
      addLine('\n⚙️  Initializing Arena interactive setup wizard...', 300);
      
      addLine('\n✨ Workspace Configurations:', 900);
      addLine('   - Default Output Directory:  ./output/', 1100);
      addLine('   - Target Clip Duration:     30 - 90 seconds', 1300);
      addLine('   - Pre-flight Validation:    Enabled', 1500);
      
      addLine('\n🔑 Checking OpenAI API Connection...', 2000);
      addLine('   - Environment Key:          Found (sk-proj-***)', 2200);
      addLine('   - Target AI Model:          gpt-4o-mini', 2400);
      addLine('   ✓ API Connection status:    Active', 2600);

      addLine('\n📦 Dependency Checklist:', 3100);
      addLine('   - Node.js Environment:      v18.16.0', 3300);
      addLine('   - Python 3 Engine:          v3.11.4', 3500);
      addLine('   - FFmpeg Binary:            Installed', 3700);
      addLine('   - PySceneDetect:            Installed', 3900);

      addLine('\n✅ Workspace initialized successfully! Ready to run arena process.\n', 4400, onComplete);
    }
  },
  {
    cmdText: 'arena process podcast.mp4 --use-4layer --fast',
    terminalTitle: 'bash — arena process podcast.mp4',
    run: (addLine, addProgressLine, onComplete) => {
      addLine('\n🔍 Running pre-flight checks...', 300);
      addLine('✓ All pre-flight checks passed\n', 900);
      addLine('🎬 Processing video...\n', 1500);
      addLine('======================================================================', 2000);
      addLine('🎬 ARENA - AI-Powered Video Clip Generation (4-Layer System)', 2100);
      addLine('======================================================================', 2200);
      addLine('📹 Input:  podcast.mp4', 2300);
      addLine('📁 Output: /output', 2400);
      addLine('🎯 Target: 4 clips (30-90s each)', 2500);
      addLine('⚡ Mode:   --fast (Lossless container seeking)', 2600);
      addLine('======================================================================\n', 2700);
      
      addLine('[1/4] 📝 Transcription', 3100);
      addLine('----------------------------------------------------------------------', 3200);
      addLine('🎧 Enhancing audio quality...', 3400);
      addLine('✓ Audio enhanced and cached (podcast_enhanced.wav)', 3900);
      
      scheduleSimTimeout(() => {
        let pct = 0;
        const progressInterval = setInterval(() => {
          pct += 25;
          const bar = '█'.repeat(pct / 10) + ' '.repeat(10 - pct / 10);
          addProgressLine(`🎤 Transcribing:  ${pct}%|[${bar}]| 00:0${pct/25}`);
          
          if (pct >= 100) {
            clearInterval(progressInterval);
            
            scheduleSimTimeout(() => {
              addLine('✓ Transcription complete. Saved to transcript.json\n', 0);
              
              addLine('[2/4] 🧠 Hybrid Analysis (AI + Audio Energy)', 300);
              addLine('----------------------------------------------------------------------', 450);
              addLine('🧠 Analyzing transcript content with AI...', 700);
              addLine('   ✓ Found 4 interesting content segments', 1200);
              addLine('⚡ Analyzing audio energy peaks...', 1500);
              addLine('   ✓ Combined scoring for best content AND delivery dynamics', 1900);
              addLine('🎯 Computing hybrid scores...', 2200);
              addLine('✓ Selected top 4 clips by hybrid score\n', 2500);
              
              addLine('======================================================================', 2800);
              addLine('TOP 4 CLIPS (Hybrid Ranked)', 2900);
              addLine('======================================================================', 3000);
              addLine('   #1 - Fascinated by Power and Politics (00:00 -> 00:34) - Score: 0.92', 3100);
              addLine('   #2 - The Art of Therapy and Human Mind (00:51 -> 01:35) - Score: 0.90', 3200);
              addLine('   #3 - From Depression to Recovery (02:00 -> 02:39) - Score: 0.88', 3300);
              addLine('   #4 - Exploring Beyond Your Career (03:06 -> 03:42) - Score: 0.86\n', 3400);

              scheduleSimTimeout(() => {
                addLine('[3/4] 🎬 Professional Editing (Sentence Alignment)', 0);
                addLine('----------------------------------------------------------------------', 150);
                addLine('📝 Aligning clips to natural sentence boundaries...', 400);
                addLine('🔍 Found 6 sentence boundaries', 800);
                addLine('✓ Successfully aligned clips to prevent mid-word cuts\n', 1200);
                
                scheduleSimTimeout(() => {
                  addLine('[4/4] ✂️  Video Clip Generation', 0);
                  addLine('----------------------------------------------------------------------', 150);
                  addLine('🎬 Generating 4 clips using lossy container seeking (fast mode)...', 400);
                  
                  scheduleSimTimeout(() => {
                    let clipsExported = 0;
                    const exportInterval = setInterval(() => {
                      clipsExported++;
                      const expPct = clipsExported * 25;
                      const expBar = '█'.repeat(expPct / 10) + ' '.repeat(10 - expPct / 10);
                      addProgressLine(`✂️  Clips:  ${expPct}%|[${expBar}]| ${clipsExported}/4 exported`);
                      
                      if (clipsExported >= 4) {
                        clearInterval(exportInterval);
                        
                        scheduleSimTimeout(() => {
                          addLine('✓ Clip generation complete! Exported 4 videos.', 0);
                          
                          addLine('\n======================================================================', 300);
                          addLine('✅ ARENA PIPELINE COMPLETE', 400);
                          addLine('======================================================================', 500);
                          addLine('📂 Output Structure:', 600);
                          addLine('   /output/', 700);
                          addLine('   ├── clips/', 800);
                          addLine('   │   ├── fascinated-by-power-and-politics_001.mp4', 900);
                          addLine('   │   ├── the-art-of-therapy-and-human-mind_002.mp4', 1000);
                          addLine('   │   ├── from-depression-to-recovery_003.mp4', 1100);
                          addLine('   │   └── navigating-trauma-and-purpose-in-your-20s_004.mp4', 1200);
                          addLine('   ├── transcript.json (word-level transcript)', 1300);
                          addLine('   └── analysis_results.json (hybrid scoring outputs)', 1400);
                          addLine('\n✨ Success! Processed video in 1m 2s.\n', 1600, () => {
                            revealClipsInPanel();
                            onComplete();
                          });
                        }, 200);
                      }
                    }, 400);
                    simTimeoutIds.push(exportInterval);
                  }, 1000);
                }, 1800);
              }, 4000);
            }, 200);
          }
        }, 300);
        simTimeoutIds.push(progressInterval);
      }, 4300);
    }
  },
  {
    cmdText: 'arena format clips/ -p tiktok --crop smart --pad blur',
    terminalTitle: 'bash — arena format clips/',
    run: (addLine, addProgressLine, onComplete) => {
      addLine('\n📐 Initializing Arena Smart-Formatting Engine...', 300);
      addLine('📌 Input Source:    clips/ (4 files found)', 600);
      addLine('📱 Target Preset:   TikTok/Shorts (9:16 Vertical)', 800);
      addLine('📐 Crop Strategy:   smart (Subject-tracking)', 1000);
      addLine('🎨 Padding Style:   blur (Gaussian-blurred background expansion)\n', 1200);
      
      addLine('======================================================================', 1500);
      addLine('⏳ Formatting Progress', 1600);
      addLine('======================================================================', 1700);

      addLine('🔄 Analyzing clips/fascinated-by-power-and-politics_001.mp4', 2000);
      addLine('   - Tracking speaker coordinates...', 2200);
      addLine('   - Processing smart crop...', 2400);
      addLine('   - Applying 25px Gaussian blur padding...', 2600);
      addLine('   ✓ Exported: clips_formatted/tiktok_001.mp4 (9:16)\n', 2800);

      addLine('🔄 Analyzing clips/the-art-of-therapy-and-human-mind_002.mp4', 3200);
      addLine('   - Tracking speaker coordinates...', 3400);
      addLine('   - Processing smart crop...', 3600);
      addLine('   - Applying 25px Gaussian blur padding...', 3800);
      addLine('   ✓ Exported: clips_formatted/tiktok_002.mp4 (9:16)\n', 4000);

      addLine('🔄 Analyzing clips/from-depression-to-recovery_003.mp4', 4400);
      addLine('   - Tracking speaker coordinates...', 4600);
      addLine('   - Processing smart crop...', 4800);
      addLine('   - Applying 25px Gaussian blur padding...', 5000);
      addLine('   ✓ Exported: clips_formatted/tiktok_003.mp4 (9:16)\n', 5200);

      addLine('🔄 Analyzing clips/navigating-trauma-and-purpose_004.mp4', 5600);
      addLine('   - Tracking speaker coordinates...', 5800);
      addLine('   - Processing smart crop...', 6000);
      addLine('   - Applying 25px Gaussian blur padding...', 6200);
      addLine('   ✓ Exported: clips_formatted/tiktok_004.mp4 (9:16)\n', 6400);

      addLine('======================================================================', 6800);
      addLine('✅ FORMATTING COMPLETE', 6900);
      addLine('======================================================================', 7000);
      addLine('📱 Processed 4 clips into clips_formatted/', 7200);
      addLine('\n✨ All clips formatted to 9:16 with subject-tracking and background blurring in 18.2s.\n', 7500, onComplete);
    }
  },
  {
    cmdText: 'arena analyze interview.mov -n 8',
    terminalTitle: 'bash — arena analyze interview.mov',
    run: (addLine, addProgressLine, onComplete) => {
      addLine('\n🧠 Running Deep AI & Audio Energy Analysis...', 300);
      addLine('📹 Input:          interview.mov', 600);
      addLine('🎯 Target Count:    8 viral candidates', 800);
      addLine('⚙️ Mode:          Analysis Only (Metatags & Highlights JSON)\n', 1000);

      addLine('======================================================================', 1300);
      addLine('⏳ Analysis Pipeline', 1400);
      addLine('======================================================================', 1500);
      addLine('📝 [1/3] Speech-to-Text:   transcribing audio stream... Done.', 1800);
      addLine('🔊 [2/3] Acoustic Analysis: extracting decibel spikes... Done.', 2300);
      addLine('🧠 [3/3] LLM Evaluation:    filtering for hook potential & context... Done.\n', 2800);

      addLine('======================================================================', 3100);
      addLine('📊 TOP 8 VIRAL CANDIDATES FOUND', 3200);
      addLine('======================================================================', 3300);
      addLine('   #1 [Score: 0.94] Hook: "The one habit that defines 1%..." (01:22 -> 02:10)', 3600);
      addLine('   #2 [Score: 0.91] Hook: "Why standard systems are broken..." (05:40 -> 06:22)', 3800);
      addLine('   #3 [Score: 0.89] Hook: "Building mental resilience..." (10:15 -> 11:05)', 4000);
      addLine('   #4 [Score: 0.88] Hook: "The psychology of flow state..." (14:30 -> 15:15)', 4200);
      addLine('   #5 [Score: 0.85] Hook: "Redefining startup growth..." (18:02 -> 18:48)', 4400);
      addLine('   #6 [Score: 0.83] Hook: "Failure is a metrics problem..." (22:11 -> 22:50)', 4600);
      addLine('   #7 [Score: 0.81] Hook: "Unlocking peak performance..." (26:40 -> 27:30)', 4800);
      addLine('   #8 [Score: 0.79] Hook: "The next decade of automation..." (30:05 -> 30:52)\n', 5000);

      addLine('💾 Saved analytical metadata successfully to output/analysis_results.json.', 5400);
      addLine('\n💡 Note: Run "arena generate interview.mov output/analysis_results.json" to extract physical clips.\n', 5800, onComplete);
    }
  }
];

function startCliSimulation() {
  const outputFeed = document.getElementById('terminal-output-feed');
  const clipsPanel = document.getElementById('clips-output-panel');
  const simClipsList = document.getElementById('sim-clips-list');
  const resetBtn = document.getElementById('reset-sim-btn');
  const termTitle = document.querySelector('.terminal-title');
  
  if (!outputFeed) return;
  
  // Bind resetBtn listener once
  if (resetBtn && !resetBtn.dataset.listenerBound) {
    resetBtn.dataset.listenerBound = 'true';
    resetBtn.addEventListener('click', () => {
      clearAllSimTimeouts();
      
      clipsPanel.classList.remove('visible');
      if (simClipsList) {
        simClipsList.innerHTML = `
          <div class="clips-placeholder">
            <span class="placeholder-icon">🎬</span>
            <p>Run the terminal simulation above to generate clips</p>
          </div>
        `;
      }
      
      currentCommandIndex = 0;
      startCliSimulation();
    });
  }

  // Get current active command configuration
  const cmdConfig = commandsSequence[currentCommandIndex];
  
  // Update Terminal Window Title dynamically
  if (termTitle) {
    termTitle.textContent = cmdConfig.terminalTitle;
  }
  
  // Reset terminal body content to the prompt line only
  outputFeed.innerHTML = `<span class="terminal-prompt">$</span> <span class="typing-text" id="terminal-typed-cmd"></span><span class="terminal-cursor"></span>`;
  
  // Hide clips panel at the start of non-generation commands (and fade in on cmd 2)
  if (currentCommandIndex !== 1) {
    clipsPanel.classList.remove('visible');
  }

  let charIndex = 0;
  const cmdText = cmdConfig.cmdText;
  
  function typeCommand() {
    const typedCmdEl = document.getElementById('terminal-typed-cmd');
    if (!typedCmdEl) return;
    
    if (charIndex < cmdText.length) {
      typedCmdEl.textContent += cmdText.charAt(charIndex);
      charIndex++;
      scheduleSimTimeout(typeCommand, 50);
    } else {
      scheduleSimTimeout(runSimulationOutputs, 600);
    }
  }
  
  function runSimulationOutputs() {
    const cursor = outputFeed.querySelector('.terminal-cursor');
    if (cursor) cursor.remove();
    
    let currentLogLines = [];
    
    const promptHtml = `<span class="terminal-prompt">$</span> <span class="typing-text">${cmdText}</span>`;
    currentLogLines.push(promptHtml);
    
    function addLine(text, delay, callback) {
      scheduleSimTimeout(() => {
        currentLogLines.push(text);
        outputFeed.innerHTML = currentLogLines.join('\n') + '\n<span class="terminal-cursor"></span>';
        
        const body = document.getElementById('terminal-terminal-tab');
        if (body) {
          body.scrollTop = body.scrollHeight;
        }
        
        if (callback) callback();
      }, delay);
    }
    
    function addProgressLine(text) {
      currentLogLines[currentLogLines.length - 1] = text;
      outputFeed.innerHTML = currentLogLines.join('\n') + '\n<span class="terminal-cursor"></span>';
      
      const body = document.getElementById('terminal-terminal-tab');
      if (body) {
        body.scrollTop = body.scrollHeight;
      }
    }
    
    cmdConfig.run(addLine, addProgressLine, () => {
      // Command completed! Wait and then transition to the next command in the loop
      const waitTime = currentCommandIndex === 1 ? 8000 : 4000;
      scheduleSimTimeout(() => {
        addLine('\n$ clear', 0, () => {
          scheduleSimTimeout(() => {
            currentCommandIndex = (currentCommandIndex + 1) % commandsSequence.length;
            startCliSimulation();
          }, 800);
        });
      }, waitTime);
    });
  }
  
  scheduleSimTimeout(typeCommand, 300);
}

function revealClipsInPanel() {
  const clipsPanel = document.getElementById('clips-output-panel');
  const simClipsList = document.getElementById('sim-clips-list');
  
  if (clipsPanel && simClipsList) {
    clipsPanel.classList.add('visible');
    simClipsList.innerHTML = '';
    
    mockClipsData.forEach((clip, index) => {
      scheduleSimTimeout(() => {
        const card = document.createElement('div');
        card.className = 'clip-output-card scroll-reveal revealed';
        card.innerHTML = `
          <div class="clip-card-thumb">
            🎬
            <span class="clip-card-badge">${clip.topic}</span>
            <span class="clip-card-duration">${clip.duration}</span>
          </div>
          <div class="clip-card-body">
            <h4 class="clip-card-title">${clip.title}</h4>
            <p class="clip-card-desc">${clip.desc}</p>
            <div class="clip-card-footer">
              <span class="clip-card-score">Score: <strong>${clip.hybridScore}</strong></span>
              <button class="btn-card-action" onclick="alert('In a full installation, this preview will open and play clip_${clip.num}.mp4 with custom burnt subtitles.')">Preview Clip</button>
            </div>
          </div>
        `;
        simClipsList.appendChild(card);
      }, index * 200);
    });
  }
}

/* ==========================================================================
   6. Interactive FAQ Accordion
   ========================================================================== */
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');
  
  faqItems.forEach(item => {
    const trigger = item.querySelector('.faq-trigger');
    const answer = item.querySelector('.faq-answer');
    
    if (trigger && answer) {
      trigger.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        
        // Close all other FAQ items first for accordion effect
        faqItems.forEach(otherItem => {
          if (otherItem !== item) {
            otherItem.classList.remove('active');
            const otherAnswer = otherItem.querySelector('.faq-answer');
            const otherTrigger = otherItem.querySelector('.faq-trigger');
            if (otherAnswer) otherAnswer.style.maxHeight = null;
            if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
          }
        });
        
        // Toggle active state on clicked item
        if (isActive) {
          item.classList.remove('active');
          answer.style.maxHeight = null;
          trigger.setAttribute('aria-expanded', 'false');
        } else {
          item.classList.add('active');
          answer.style.maxHeight = answer.scrollHeight + 'px';
          trigger.setAttribute('aria-expanded', 'true');
        }
      });
    }
  });
}
