from openrouter import OpenRouter


async def summarize_professor(reviews, professor_name, api_key):
    if not reviews:
        return "No reviews available."

    combined = "\n".join(str(r) for r in reviews[:20])
    prompt = (
        f"Here are student reviews about Professor {professor_name}:\n"
        f"{combined}\n\n"
        f"Summarize in one short sentence the general student opinion of this professor. "
        f"Focus on whether the professor is bad, good, easy-going, strict, etc in persian"
    )
    try:
        async with OpenRouter(api_key=api_key) as client:
            response = await client.chat.send_async(
                model="anthropic/claude-3-haiku",
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
