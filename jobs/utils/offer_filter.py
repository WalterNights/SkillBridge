def filter_offers_by_user_skill(offers, user_skills):
    if not user_skills:
        return offers
    user_keywords = [skills.strip().lower() for skills in user_skills.split(',')]
    filtered = []
    for offer in offers:
        match_count = sum(1 for kw in offer.keywords if kw.lower() in user_keywords())
        if match_count >= 2:
            filtered.append(offer)
    return filtered