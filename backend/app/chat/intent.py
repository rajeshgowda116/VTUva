import re

def detect_intent(message: str) -> str:
    if not message:
        return "UNKNOWN"

    text_clean = re.sub(r"[!.,?]", "", message.strip().lower()).strip()
    if not text_clean:
        return "UNKNOWN"

    # Base Greetings set
    greetings = {
        "hi", "hii", "hiii", "hello", "helloo", "hey", "heyy", "heyyy",
        "hi vtuva", "hello vtuva", "hey vtuva", "good morning", "good afternoon",
        "good evening", "hola", "namaste", "howdy"
    }

    # Normalize trailing repeated characters e.g. "hiii" -> "hi", "heyyy" -> "hey"
    norm_text = re.sub(r"(.)\1+", r"\1", text_clean)

    # Greeting regex matching (e.g. hi+, hello+, hey+)
    if (
        text_clean in greetings or 
        norm_text in greetings or 
        re.match(r"^(h+[iea]+y*|hello+|hola+|namaste|good\s*(morning|afternoon|evening))$", text_clean)
    ):
        return "GREETING"

    # Casual Gratitude
    thanks_set = {
        "thanks", "thank you", "thx", "thank u", "ty", "thank you so much",
        "thanks a lot", "many thanks", "thanks vtuva", "thank you vtuva"
    }
    if text_clean in thanks_set or norm_text in thanks_set:
        return "CASUAL_THANKS"

    # Casual Positive / Approval
    good_set = {
        "good", "nice", "great", "awesome", "cool", "fine", "perfect",
        "super", "wonderful", "excellent", "brilliant", "amazing"
    }
    if text_clean in good_set or norm_text in good_set:
        return "CASUAL_GOOD"

    # Casual Confirmation / Acknowledgment
    ok_set = {
        "okay", "ok", "got it", "understood", "alright", "sure", "k", "kk",
        "makes sense", "gotcha", "right"
    }
    if text_clean in ok_set or norm_text in ok_set:
        return "CASUAL_OK"

    return "UNKNOWN"

