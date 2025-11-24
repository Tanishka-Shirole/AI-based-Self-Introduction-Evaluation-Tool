import streamlit as st
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from lexicalrichness import LexicalRichness

# Try importing LanguageTool; if not available, we fall back gracefully
try:
    import language_tool_python
    LT_AVAILABLE = True
except ImportError:
    LT_AVAILABLE = False

# ---------------- SALUTATION ----------------
def salutation_score(text):
    first_line = text.lower().strip()

    excellent_phrases = ["excited to introduce", "feeling great"]
    good_phrases = ["good morning", "good afternoon", "good evening", "good day", "hello everyone"]
    normal_phrases = ["hi", "hello"]

    if any(p in first_line for p in excellent_phrases):
        return 5, "Excellent salutation detected."
    elif any(p in first_line for p in good_phrases):
        return 4, "Good salutation."
    elif any(p in first_line for p in normal_phrases):
        return 2, "Normal salutation."
    else:
        return 0, "No clear salutation."


# ---------------- KEYWORD PRESENCE ----------------
def keyword_presence_score(text):
    t = text.lower()
    score = 0
    feedback = []

    must_have = {
        "Name": ["my name is", "myself"],
        "Age": ["years old"],
        "School/Class": ["class", "school", "grade"],
        "Family": ["my family", "father", "mother", "parents"],
        "Hobbies": [
            "i enjoy", "i enjoy playing", "i really enjoy",
            "i like", "i like to", "i like playing",
            "i love", "i love to", "i love playing",
            "my hobby", "my hobbies",
            "one thing i enjoy", "one thing i like",
            "playing cricket", "playing football", "playing games",
            "i like doing", "i enjoy doing"
        ]
    }

    for label, kws in must_have.items():
        if any(k in t for k in kws):
            score += 4
            feedback.append(f"{label}: found (+4)")
        else:
            feedback.append(f"{label}: missing")

    good_to_have = {
        "Family Details": ["there are", "we are"],
        "Origin Location": ["i am from", "we are from"],
        "Ambition/Goal": ["i want to become", "my dream is"],
        "Fun Fact": ["fun fact"],
        "Strengths/Achievements": ["my strength", "i have achieved"]
    }

    for label, kws in good_to_have.items():
        if any(k in t for k in kws):
            score += 2
            feedback.append(f"{label}: included (+2)")

    return score, " | ".join(feedback)


# ---------------- FLOW ----------------
def flow_score(text):
    t = text.lower()

    salutation_pos = t.find("hello")
    if salutation_pos == -1:
        salutation_pos = t.find("hi")

    name_pos = t.find("my name")
    if name_pos == -1:
        name_pos = t.find("myself")

    closing_pos = t.rfind("thank you")

    if salutation_pos != -1 and name_pos != -1 and salutation_pos < name_pos < closing_pos:
        return 5, "Flow is correct (Salutation → Details → Closing)."
    else:
        return 0, "Flow not followed correctly."


# ---------------- SPEECH RATE ----------------
def speech_rate_score(word_count, duration_sec):
    if duration_sec <= 0:
        return 0, "Invalid duration."

    wpm = word_count / (duration_sec / 60)

    if wpm > 161:
        return 2, f"Speech Rate = {wpm:.1f} WPM (Too Fast)"
    elif 141 <= wpm <= 160:
        return 6, f"Speech Rate = {wpm:.1f} WPM (Fast)"
    elif 111 <= wpm <= 140:
        return 10, f"Speech Rate = {wpm:.1f} WPM (Ideal)"
    elif 81 <= wpm <= 110:
        return 6, f"Speech Rate = {wpm:.1f} WPM (Slow)"
    else:
        return 2, f"Speech Rate = {wpm:.1f} WPM (Too Slow)"


# ---------------- SIMPLE GRAMMAR (NO JAVA REQUIRED) ----------------
def grammar_score_simple(text, word_count):
    if word_count == 0:
        return 0, "No words."

    sentences = re.split(r'[.!?]+', text)
    errors = 0

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if not s[0].isupper():
            errors += 1

    errors += text.count(" i ")

    if not text.strip().endswith(('.', '!', '?')):
        errors += 1

    errors_per_100 = (errors / word_count) * 100
    grammar_value = 1 - min(errors_per_100 / 10, 1)

    if grammar_value > 0.9:
        marks = 10
    elif 0.7 <= grammar_value <= 0.89:
        marks = 8
    elif 0.5 <= grammar_value <= 0.69:
        marks = 6
    elif 0.3 <= grammar_value <= 0.49:
        marks = 4
    else:
        marks = 2

    return marks, f"[Simple] Estimated grammar issues: {errors} (grammar value = {grammar_value:.2f})"


# ---------------- GRAMMAR WITH LANGUAGETOOL ----------------
def grammar_score_languagetool(text, word_count):
    """
    Uses LanguageTool if available & working.
    Returns (marks, feedback) or (None, error_msg) if it fails.
    """
    if not LT_AVAILABLE:
        return None, "[LanguageTool] Not installed. Using simple grammar only."

    if word_count == 0:
        return None, "[LanguageTool] No words."

    try:
        tool = language_tool_python.LanguageTool('en-US')
        matches = tool.check(text)
        error_count = len(matches)
    except Exception as e:
        return None, f"[LanguageTool] Error: {e}. Falling back to simple grammar."

    errors_per_100 = (error_count / word_count) * 100
    grammar_value = 1 - min(errors_per_100 / 10, 1)

    if grammar_value > 0.9:
        marks = 10
    elif 0.7 <= grammar_value <= 0.89:
        marks = 8
    elif 0.5 <= grammar_value <= 0.69:
        marks = 6
    elif 0.3 <= grammar_value <= 0.49:
        marks = 4
    else:
        marks = 2

    feedback = f"[LanguageTool] Errors: {error_count}, grammar value = {grammar_value:.2f}"
    return marks, feedback


# ---------------- VOCABULARY (MTLD using LexicalRichness) ----------------
def vocabulary_score(text):
    lex = LexicalRichness(text)
    mtld_value = lex.mtld()   # MTLD score

    if mtld_value >= 80:
        marks = 10
    elif mtld_value >= 60:
        marks = 8
    elif mtld_value >= 40:
        marks = 6
    elif mtld_value >= 20:
        marks = 4
    else:
        marks = 2

    feedback = f"MTLD = {mtld_value:.2f}"
    return marks, feedback


# ---------------- FILLER WORDS ----------------
def filler_word_score(text):
    filler_words = ["um", "uh", "like", "you know", "so", "actually", "basically",
                    "right", "i mean", "well", "kinda", "sort of", "okay", "hmm", "ah"]

    words = text.lower().split()
    total = len(words)
    if total == 0:
        return 0, "No words."

    filler_count = sum(words.count(f) for f in filler_words)
    rate = (filler_count / total) * 100

    if rate <= 3:
        marks = 15
    elif rate <= 6:
        marks = 12
    elif rate <= 9:
        marks = 9
    elif rate <= 12:
        marks = 6
    else:
        marks = 3

    return marks, f"Filler words: {filler_count} (Rate = {rate:.2f}%)"


# ---------------- SENTIMENT (USING VADER, COMPOUND→0–1) ----------------
def sentiment_score(text):
    analyzer = SentimentIntensityAnalyzer()
    result = analyzer.polarity_scores(text)

    # Convert compound score (-1 to 1) → positivity (0 to 1)
    score = (result["compound"] + 1) / 2

    if score >= 0.9:
        marks = 15
    elif 0.7 <= score < 0.9:
        marks = 12
    elif 0.5 <= score < 0.7:
        marks = 9
    elif 0.3 <= score < 0.5:
        marks = 6
    else:
        marks = 3

    return marks, f"Positivity Score: {score:.2f}"


# ---------------- SUGGESTION GENERATOR ----------------
def generate_suggestions(
    total, sal_score, key_score, flow_s,
    speech_s, grammar_s, vocab_s, filler_s, sent_s
):
    suggestions = []

    # Overall
    if total >= 90:
        suggestions.append("Excellent overall introduction! You can keep practicing to maintain this level.")
    elif total >= 75:
        suggestions.append("Good introduction overall. A few small improvements can make it even better.")
    else:
        suggestions.append("Your introduction has a good base. With a few improvements, it can become much stronger.")

    # Salutation
    if sal_score < 5:
        suggestions.append("Try starting with a more engaging salutation, like 'Good morning everyone, I am excited to introduce myself...'.")

    # Keywords
    if key_score < 30:
        suggestions.append("Include more details like your goals, strengths, or an achievement to make the introduction richer.")

    # Flow
    if flow_s < 5:
        suggestions.append("Organize your introduction in order: greeting → basic details → extra details → closing thank you.")

    # Speech rate
    if speech_s < 10:
        suggestions.append("Practice speaking at a slightly more natural pace. Record yourself and try to stay in a comfortable speed range.")

    # Grammar
    if grammar_s < 10:
        suggestions.append("Review basic grammar and sentence structure. Reading your introduction aloud or using a grammar checker can help.")

    # Vocabulary
    if vocab_s < 10:
        suggestions.append("Try using a wider range of words instead of repeating the same ones. Reading books and articles can help build vocabulary.")

    # Filler words
    if filler_s < 15:
        suggestions.append("Reduce filler words like 'um', 'like', or 'you know'. Pause briefly instead of using fillers.")

    # Sentiment / engagement
    if sent_s < 15:
        suggestions.append("Sound more enthusiastic and positive about yourself. Smiling while speaking can naturally improve your tone.")

    return suggestions


# ---------------- UI ----------------
st.title("Self-Introduction Scoring Tool")

with st.expander("ℹ️ About This Evaluation Tool"):
    st.write("""
    This tool evaluates a student's spoken self-introduction. 
      
    It analyzes the transcript across **8 major scoring categories**:

    ---

    ### **1️⃣ Content & Structure**
    **A. Salutation (5 marks)**  
    Detects how the student begins the introduction:  
    - Excellent: “I am excited to introduce myself…”  
    - Good: “Good morning / Hello everyone”  
    - Normal: “Hi / Hello”  

    **B. Keyword Presence (30 marks)**  
    Checks if the introduction includes required fields:  
    - **Must-Have (4 marks each)**: Name, Age, School/Class, Family, Hobbies  
    - **Good-to-Have (2 marks each)**: Family details, Location, Goal/Ambition, Fun fact, Strength/Achievements  

    **C. Flow (5 marks)**  
    Correct order must be:  
    **Salutation → Basic details → Extra details → Closing**  

    ---

    ### **2️⃣ Delivery**
    **A. Speech Rate (10 marks)**  
    - Ideal (111–140 WPM) = 10  
    - Fast / Slow = lower score  

    **B. Clarity – Filler Words (15 marks)**  
    Counts fillers like: *um, uh, like, you know, actually, basically, right,* etc.  
    Lower fillers → higher score.  

    ---

    ### **3️⃣ Language Quality**
    **A. Grammar (10 marks)**  
    This tool uses a **dual-model approach**:  
    - **LanguageTool (Java-based NLP grammar engine)**  
    - **Simple rule-based model (capitalization, punctuation, basic rules)**  

    Whichever model gives the **better score** is chosen automatically.  
    This ensures fairness and robustness even if one model fails.

    **B. Vocabulary Richness (10 marks)**  
    Uses **MTLD (Measure of Textual Lexical Diversity)**  
    Higher MTLD → richer vocabulary.

    ---

    ### **4️⃣ Engagement (15 marks)**
    **Sentiment Analysis (VADER)**  
    Measures positivity and emotional tone of the introduction.  
    Higher positivity → higher score.

    ---

    ### **Final Scoring**
    The system combines all category scores to generate a **final score out of 100**,  
    following the exact weightage defined in the Nirmaan rubric.

    This design ensures:  
    - High accuracy  
    - Transparency  
    - Robustness  
    - Easy interpretation for teachers and evaluators  
    """)

st.write(
    "Paste a student's self-introduction transcript and duration. "
    "The tool will score it based on the rubric (content, structure, delivery, and engagement)."
)

transcript = st.text_area("📄 Paste transcript here:", height=200, placeholder="Paste the student's introduction text...")
duration = st.number_input("⏱️ Enter duration in seconds:", min_value=1, value=52)

if st.button("Score"):
    if not transcript.strip():
        st.warning("Please paste a transcript first!")
    else:
        st.success("Scoring your introduction...")

        words = transcript.split()
        word_count = len(words)

        # ---- CORE SCORES ----
        sal_score, sal_feedback = salutation_score(transcript)
        key_score, key_feedback = keyword_presence_score(transcript)
        flow_s, flow_fb = flow_score(transcript)
        speech_s, speech_fb = speech_rate_score(word_count, duration)

        lt_grammar_s, lt_grammar_fb = grammar_score_languagetool(transcript, word_count)
        simple_grammar_s, simple_grammar_fb = grammar_score_simple(transcript, word_count)

        # Final grammar score = best of both (if LT available)
        if lt_grammar_s is not None:
            grammar_s = max(lt_grammar_s, simple_grammar_s)
            chosen_source = "LanguageTool" if lt_grammar_s >= simple_grammar_s else "Simple Model"
        else:
            grammar_s = simple_grammar_s
            chosen_source = "Simple Model (fallback)"

        vocab_s, vocab_fb = vocabulary_score(transcript)
        filler_s, filler_fb = filler_word_score(transcript)
        sent_s, sent_fb = sentiment_score(transcript)

        total = sal_score + key_score + flow_s + speech_s + grammar_s + vocab_s + filler_s + sent_s

        # ---------- SUMMARY DASHBOARD ----------
        st.header("📊 Score Summary")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Salutation", f"{sal_score}/5")
            st.metric("Flow", f"{flow_s}/5")
        with col2:
            st.metric("Keywords", f"{key_score}/30")
            st.metric("Speech Rate", f"{speech_s}/10")
        with col3:
            st.metric("Grammar (Final)", f"{grammar_s}/10")
            st.metric("Vocabulary", f"{vocab_s}/10")
        with col4:
            st.metric("Clarity (Filler)", f"{filler_s}/15")
            st.metric("Sentiment", f"{sent_s}/15")

        st.markdown("---")
        st.subheader(f"🎉 Final Overall Score: **{total} / 100**")

        # ---------- DETAILED BREAKDOWN ----------
        st.markdown("### 📂 Detailed Breakdown")

        # Content & Structure
        st.markdown("#### 1️⃣ Content & Structure")
        st.write("**Salutation**")
        st.write(f"- Score: {sal_score} / 5")
        st.write(f"- Feedback: {sal_feedback}")

        st.write("**Keyword Presence**")
        st.write(f"- Score: {key_score} / 30")
        st.write(f"- Feedback: {key_feedback}")

        st.write("**Flow**")
        st.write(f"- Score: {flow_s} / 5")
        st.write(f"- Feedback: {flow_fb}")

        # Delivery
        st.markdown("#### 2️⃣ Delivery & Clarity")
        st.write("**Speech Rate**")
        st.write(f"- Score: {speech_s} / 10")
        st.write(f"- Feedback: {speech_fb}")

        st.write("**Clarity (Filler Words)**")
        st.write(f"- Score: {filler_s} / 15")
        st.write(f"- Feedback: {filler_fb}")

        # Grammar
        st.markdown("#### 3️⃣ Language & Grammar (Comparison)")
        if lt_grammar_s is not None:
            st.write(f"LanguageTool Score: {lt_grammar_s} / 10")
            st.write(f"Details: {lt_grammar_fb}")
        else:
            st.write("LanguageTool Score: N/A")
            st.write(lt_grammar_fb)

        st.write(f"Simple Model Score: {simple_grammar_s} / 10")
        st.write(f"Details: {simple_grammar_fb}")

        st.markdown(
            f"**Final Grammar Score Used:** {grammar_s} / 10  \n"
            f"_Source: {chosen_source}_"
        )

        # Vocabulary & Sentiment
        st.markdown("#### 4️⃣ Vocabulary & Engagement")
        st.write("**Vocabulary Richness**")
        st.write(f"- Score: {vocab_s} / 10")
        st.write(f"- Feedback: {vocab_fb}")

        st.write("**Engagement / Sentiment**")
        st.write(f"- Score: {sent_s} / 15")
        st.write(f"- Feedback: {sent_fb}")

        # ---------- SUGGESTIONS ----------
        st.markdown("### 💡 Suggestions for the Student")
        suggestions = generate_suggestions(
            total, sal_score, key_score, flow_s,
            speech_s, grammar_s, vocab_s, filler_s, sent_s
        )

        if suggestions:
            for s in suggestions:
                st.markdown(f"- {s}")
        else:
            st.write("Great job! No major improvements needed.")
