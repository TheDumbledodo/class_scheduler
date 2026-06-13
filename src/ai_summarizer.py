from openrouter import OpenRouter


async def summarize_professor(reviews, professor_name, api_key, model="deepseek/deepseek-chat"):
    if not reviews:
        return "No reviews available."

    formatted = []
    for i, r in enumerate(reviews[:20], 1):
        parts = ['Student {}: "{}"'.format(i, r.get("review", r.get("text", "")))]
        course = r.get('course', '')
        if course:
            parts.append('(course: {})'.format(course))

        reactions = r.get('reactions', [])
        if reactions:
            rtxt = ', '.join("{}x{}".format(rt['emoji'], rt['count']) for rt in reactions)
            parts.append('[reactions: {}]'.format(rtxt))

        formatted.append(' '.join(parts))

    combined = "\n".join(formatted)

    prompt = f"""
    Here are student reviews about Professor {professor_name}:

    {combined}

    Task:
    - Infer sentiment ONLY from review TEXT (ignore reactions for direction).
    - Reactions (👍 ❤️ 👎 😂 💩) are ONLY confidence signals, not opinion signals.

    Important interpretation rule:
    - Strong negative language (e.g. بد، افتضاح، تدریس ضعیف، نمره‌دهی سخت/بد، امتحان سخت) should be treated as strong negative even if reactions are mixed.
    - A single clearly positive review does NOT override multiple negative reviews.

    Aggregation logic:
    - Determine sentiment per review first (positive / negative / neutral).
    - Then aggregate:
      * If most reviews are negative → overall negative
      * If most reviews are positive → overall positive
      * Otherwise → mixed (but only if genuinely balanced)

    Decision bias rule:
    - If there is a clear majority sentiment, DO NOT output mixed.

    Output rules:
    - Write 2–3 sentences in Persian.
    - Mention Professor {professor_name} naturally in the text.
    - Do NOT include numbers, percentages, or vote counts.
    - Avoid neutral wording when sentiment is clearly negative or positive.
    - Output only the final text.
    """
    try:
        async with OpenRouter(api_key=api_key) as client:
            response = await client.chat.send_async(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarises professor reviews."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI summary unavailable: {str(e)}"
