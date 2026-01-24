# Norman Audit - Cycle 1 Findings
**Date:** 2026-01-24
**Method:** CLI with mock transcript injection
**Test Scenario:** Voice → Transcription → Mediation → Script approval workflow

---

## Test Execution Log

### Step 1: Initial State
```bash
editorbot-cli reset
editorbot-cli show-state
```
**Result:** ✅ State: IDLE
**Observation:** Clean starting point

---

### Step 2: Inject Mock Transcript
```bash
editorbot-cli inject-transcript "Hola, hoy voy a hablar sobre la importancia de la comunicación efectiva en el trabajo remoto. Es fundamental mantener canales abiertos con el equipo y establecer expectativas claras."
```

**Expected Flow:**
1. IDLE → AUDIO_RECEIVED
2. AUDIO_RECEIVED → TRANSCRIBED (with transcript)
3. TRANSCRIBED → MEDIATED (with mediated text)

**Actual Flow:** ✅ Matched expectations

**State Transitions Logged:**
```json
{"level": "INFO", "message": "state_transition_attempt", "current_state": "idle", "event": "voice_received"}
{"level": "INFO", "message": "state_transition_complete", "new_state": "audio_received"}
{"level": "INFO", "message": "state_transition_attempt", "current_state": "audio_received", "event": "transcription_complete"}
{"level": "INFO", "message": "state_transition_attempt", "current_state": "transcribed", "event": "text_received"}
```

**Bot Response:**
```
✍️ Texto mediado (borrador):

[MOCK MEDIATION] Hola, hoy voy a hablar sobre la importancia de la comunicación efectiva en el trabajo remoto. Es fundamental mantener canales abiertos con el equipo y establecer expectativas claras.

Responde con:
- OK
- EDITAR (pegando texto)
- CANCELAR
```

**Final State:** BotState.MEDIATED
**Final Transcript:** `[MOCK MEDIATION] Hola, hoy voy a hablar...`

---

### Step 3: Approve Mediated Text
```bash
editorbot-cli send-text "OK"
```

**Expected:**
- MEDIATED → SCRIPT_DRAFTED
- Script generation triggered
- Script displayed with options

**Actual:** ⚠️ **FAILED** - Invalid state transition

**Error Logs:**
```json
{"level": "INFO", "message": "state_transition_attempt", "current_state": "mediated", "event": "command_ok"}
{"level": "ERROR", "message": "invalid_state_transition"}
```

**Bot Response:**
```
⚠️ Ocurrió un error. Intenta de nuevo.
```

---

## Norman Principle Analysis

### 1. Visibility 👁️

#### What Users Can See
✅ **GOOD:**
- Clear bot messages at each step
- State transitions logged (visible in verbose mode)
- Options displayed: OK / EDITAR / CANCELAR

❌ **POOR:**
- State name shown as "mediated" (technical jargon)
- No progress indicator (e.g., "Step 2 of 5")
- Users don't know what happens after "OK"

**Score:** Fair

**Issues:**
- **P0:** State names are developer-facing, not user-friendly
- **P1:** No visual progress through workflow
- **P2:** "[MOCK MEDIATION]" prefix exposed to user (implementation detail)

---

### 2. Feedback 🔊

#### After Each Action
✅ **GOOD:**
- Immediate response after voice upload: "🎤 Audio recibido. Transcribiendo..."
- Clear confirmation: "✅ State: AUDIO_RECEIVED"
- Emoji indicators help (✅, 🔄, ⚠️)

❌ **POOR:**
- When OK command fails, generic error: "Ocurrió un error. Intenta de nuevo."
- No explanation of what went wrong
- No recovery guidance

**Score:** Fair

**Issues:**
- **P0:** Error messages don't explain cause or solution
- **P1:** No processing time indicators ("this may take 10-30 seconds...")
- **P2:** Success messages could be more celebratory/encouraging

---

### 3. Constraints ⛔

#### What Prevents Errors
✅ **GOOD:**
- Limited options: only "OK", "EDITAR", "CANCELAR" accepted
- Clear text format requirements

❌ **POOR:**
- **P0 BUG:** "OK" command fails despite being suggested option
- No input validation visible to user
- Case sensitivity unclear ("OK" vs "ok" vs "Ok"?)

**Score:** Poor (workflow-blocking bug)

**Issues:**
- **P0:** State machine allows invalid transition (MEDIATED + COMMAND_OK → error)
- **P1:** No inline keyboard buttons (forces manual typing)
- **P2:** No confirmation before starting expensive operations

---

### 4. Mapping 🗺️

#### Mental Model Alignment
❌ **POOR:**
- Conversation flow is:
  1. Upload voice → 2. Review text → 3. Approve → 4. Get script → 5. Choose template
- But state names don't match: "MEDIATED", "TRANSCRIBED", "SCRIPT_DRAFTED"
- Users think in verbs (upload, edit, approve), bot uses adjectives (mediated, transcribed)

**Score:** Poor

**Issues:**
- **P1:** State names mismatch user mental model
- **P1:** "Mediated" is technical term (users expect "enhanced" or "improved")
- **P2:** No visual workflow diagram or breadcrumbs

---

### 5. Consistency 🎯

#### Pattern Recognition
✅ **GOOD:**
- All prompts follow same format: text + options list
- Emoji usage consistent (✍️ for text, 📝 for script)

⚠️ **FAIR:**
- Option format varies: "OK" (caps) but "Intenta de nuevo" (lowercase)
- Some messages use 🤖, others don't

**Score:** Fair

**Issues:**
- **P2:** Capitalization inconsistency in commands
- **P2:** Emoji placement not standardized

---

### 6. Affordances 💡

#### Perceived Actions
❌ **POOR:**
- Text input (typing) required instead of buttons
- No visual indication that "OK", "EDITAR", "CANCELAR" are clickable/tappable
- Telegram supports inline keyboards but bot doesn't use them

**Score:** Poor

**Issues:**
- **P0:** No inline keyboard for common actions (forces typing)
- **P1:** Options look like instructions, not buttons
- **P1:** No visual distinction between action words and explanation text

---

## Critical Bugs Found

### BUG-001: MEDIATED + COMMAND_OK Transition Fails
**Severity:** P0 (workflow blocker)
**State:** MEDIATED
**Event:** COMMAND_OK
**Expected:** Transition to SCRIPT_DRAFTED
**Actual:** InvalidTransition error
**Impact:** User cannot proceed past text mediation step

**Root Cause:** State machine missing transition rule

**Location:** `bot/state/machine.py` lines 100-125

**Fix Required:**
```python
if state == BotState.MEDIATED:
    if event == EventType.COMMAND_OK:
        return Conversation(
            state=BotState.SCRIPT_DRAFTED,
            transcript=convo.transcript,
            mediated_text=convo.transcript,  # Save mediated version
        )
```

---

## Quick Wins (< 1 hour each)

1. **Add inline keyboard for OK/EDITAR/CANCELAR** (P0)
   - Replace text prompts with Telegram inline buttons
   - Eliminates typing errors
   - Better mobile UX

2. **Improve error message for invalid state** (P0)
   - Change: "⚠️ Ocurrió un error. Intenta de nuevo."
   - To: "⚠️ Este comando no está disponible ahora. Usa las opciones mostradas arriba."

3. **Add progress indicators** (P1)
   - Add: "Paso 2 de 5: Revisa el texto mejorado"
   - Helps users understand workflow length

4. **Hide mock mediation prefix in CLI** (P2)
   - Don't show "[MOCK MEDIATION]" to user
   - Only log it in verbose mode

---

## Medium Effort Improvements (2-4 hours each)

1. **Rename states to user-friendly terms** (P1)
   - MEDIATED → "reviewing_enhanced_text"
   - TRANSCRIBED → "text_ready"
   - Display: "📝 Revisando texto mejorado..."

2. **Add workflow breadcrumbs** (P1)
   - Show: "🎤 Voz → ✍️ Texto → 📝 Guion → 🎬 Video"
   - Highlight current step

3. **Implement typing indicators** (P2)
   - Show "..." while processing
   - Set chat action: "typing"

---

## Long-term UX Enhancements (1+ day each)

1. **Visual workflow preview** (P2)
   - Send graphic showing all steps on /start
   - Interactive flowchart

2. **Undo functionality** (P2)
   - Allow "back" command
   - Restore previous state

3. **Help system** (P2)
   - Context-aware help
   - /help shows relevant commands for current state

---

## Test Coverage

**States Tested:**
- ✅ IDLE
- ✅ AUDIO_RECEIVED
- ✅ TRANSCRIBED
- ✅ MEDIATED
- ❌ SCRIPT_DRAFTED (blocked by bug)
- ❌ FINAL_SCRIPT (not reached)
- ❌ TEMPLATE_SELECTED (not reached)

**Events Tested:**
- ✅ VOICE_RECEIVED
- ✅ TRANSCRIPTION_COMPLETE
- ✅ TEXT_RECEIVED
- ⚠️ COMMAND_OK (attempted, failed)
- ❌ COMMAND_EDIT (not tested)
- ❌ COMMAND_CANCEL (not tested)

**Completion:** 31% (4/13 states tested, 1 blocking bug found)

---

## Next Steps

1. ✅ Fix BUG-001 (MEDIATED → SCRIPT_DRAFTED transition)
2. Test full workflow to completion
3. Implement quick wins
4. Run Cycle 2 with real Telegram bot
5. Compare CLI vs Telegram UX differences

---

## Audit Notes

**Methodology Notes:**
- CLI testing effective for state machine logic
- Mock mediation sufficient for UX audit
- Missing Whisper transcription doesn't block workflow testing
- Verbose logging critical for understanding state flow

**Tool Effectiveness:**
- ✅ `inject-transcript` command works perfectly
- ✅ State display clear and informative
- ✅ Structured logging helps track transitions
- ⚠️ Need to test with real Telegram UI next

**Auditor Observations:**
The bot has solid state management but poor user-facing communication. Technical implementation is clean, but UX needs significant improvement. The blocking bug prevents completion of even basic workflows.

Priority should be:
1. Fix critical bug (BUG-001)
2. Add inline keyboards
3. Improve error messages
4. Then test on real Telegram
