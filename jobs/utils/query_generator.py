def extract_search_query_from_summary(summary):
    """
    Extracts a search query from the job offer summary.
    This function looks for specific keywords in the summary to form a search query.
    """
    if not summary:
       return ""
    summary = summary.lower()
    common_keywords = [
        "desarrollador", "ingeniero", "analista", "programador",
        "frontend", "backend", "fullstack", "qa", "devops", "soporte", 
        "data", "inteligencia", "seguridad", "cloud", "scrum"
    ]
    for keyword in common_keywords:
        if keyword in summary:
            return keyword

    # Fallback: the most large word in the summary
    words = summary.split()
    return max(words, key=len) if words else ""