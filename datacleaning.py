import argparse
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
from google import genai


class GenAIModelAdapter:
    def __init__(self, client, model_name):
        self._client = client
        self._model_name = model_name

    def generate_content(self, prompt):
        return self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )

def build_clients():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment.")
    # Support both the legacy google.generativeai API and the newer google-genai API.
    if hasattr(genai, "configure") and hasattr(genai, "GenerativeModel"):
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-3-flash-preview")
    if hasattr(genai, "Client"):
        client = genai.Client(api_key=api_key)
        return GenAIModelAdapter(client, "gemini-3-flash-preview")
    raise RuntimeError(
        "Unsupported google.genai module: missing configure/GenerativeModel and Client."
    )



def fetch_openreview_notes(forum_id):
    """Fetch notes for a forum id from OpenReview without external deps."""
    base_url = "https://api2.openreview.net/notes"
    query = urllib.parse.urlencode({"forum": forum_id})
    url = f"{base_url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "worst-paper-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = resp.read().decode("utf-8")
            data = json.loads(payload)
            return data.get("notes", [])
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Network error: {e.reason}"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON from OpenReview API."}


def get_review_text(paper_id):
    """Fetches the actual review text from OpenReview API."""
    try:
        notes = fetch_openreview_notes(paper_id)
        if isinstance(notes, dict) and "error" in notes:
            return f"Could not fetch reviews: {notes['error']}"
        # We only want the 'official reviews'
        reviews = [n for n in notes if 'review' in n.get("invitation", "").lower()]
        full_text = ""
        for i, r in enumerate(reviews):
            # Extract weaknesses specifically if available
            content = r.get("content", {})
            weakness = content.get('weaknesses', {}).get('value', '')
            full_text += f"\nReviewer {i + 1} Weaknesses: {weakness}\n"
        return full_text
    except Exception as e:
        return f"Could not fetch reviews: {e}"


def generate_roast(model, paper_data, review_text):
    prompt = f"""
    You are an expert AI researcher with a sharp, witty sense of humor. 
    Translate this rejected academic paper's failure into 'Real Talk' for laymen.

    PAPER TITLE: {paper_data['title']}
    ABSTRACT: {paper_data['abstract']}
    REVIEWS: {review_text}

    OUTPUT FORMAT: 
    Return ONLY a JSON object with the following keys:
    - "laymen_summary": A 2-sentence summary based on the abstract.
    - "why_bad": A list of 3 major critiques from the reviews.
    - "analogy_name": A funny, catchy name for the analogy.
    - "analogy_description": The full analogy text.

    TONE: Adaptive, witty, grounded, and slightly snarky but scientifically accurate.
    """
    response = model.generate_content(prompt)
    if hasattr(response, "text") and response.text:
        return response.text
    # Fallbacks for alternate response shapes.
    if hasattr(response, "candidates") and response.candidates:
        parts = []
        for cand in response.candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            for part in getattr(content, "parts", []):
                text = getattr(part, "text", "")
                if text:
                    parts.append(text)
        if parts:
            return "\n".join(parts)
    return str(response)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate roasts for rejected papers.")
    parser.add_argument(
        "--input",
        default="failed_iclr2026.json",
        help="Input JSON file (list of paper objects).",
    )
    parser.add_argument(
        "--output",
        default="failed_iclr2026_roasts_trial.json",
        help="Output JSON file for generated roasts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of items to process from the input file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    model = build_clients()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for paper in data[: args.limit]:
        print(f"Roasting: {paper.get('title', 'Untitled')}...")
        try:
            actual_reviews = get_review_text(paper["id"])
            roast = generate_roast(model, paper, actual_reviews)
            results.append(
                {
                    "id": paper.get("id"),
                    "title": paper.get("title"),
                    "roast": roast,
                    "review_text": actual_reviews,
                }
            )
        except Exception as e:
            results.append(
                {
                    "id": paper.get("id"),
                    "title": paper.get("title"),
                    "error": str(e),
                }
            )

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(results)} items to {output_path}")


if __name__ == "__main__":
    main()
