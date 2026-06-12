import openai


def summarize_professor(reviews, professor_name, api_key):
    if not reviews:
        return "No reviews available."

    openai.api_key = api_key
    openai.api_base = "https://openrouter.ai/api/v1"

    combined = "\n".join(str(r) for r in reviews[:20])
    prompt = (
        f"Here are student reviews about Professor {professor_name}:\n"
        f"{combined}\n\n"
        f"Summarize in one short sentence the general student opinion of this professor. "
        f"Focus on whether the professor is bad, good, easy-going, strict, etc in persian"
    )
    try:
        response = openai.ChatCompletion.create(
            model="anthropic/claude-3-haiku",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarises professor reviews."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=80,
            temperature=0.3,
            headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "ClassScheduler"
            }
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI summary unavailable: {str(e)}"
