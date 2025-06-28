from thefuzz import process
import requests

def find_closest_match(query: str, choices: list[str]) -> str:
    """
    Finds the best match for a query string from a list of choices.

    Args:
        query: The string you want to find a match for.
        choices: A list of strings to search through.

    Returns:
        The best matching string from the choices list, or None if choices is empty.
    """
    if not choices:
        raise ValueError("No choices provided. (options are not close enough)")
    
    # extractOne returns a tuple: (best_match, score)
    best_match = process.extractOne(query, choices)[0]
    
    return best_match

def get_fun_fact():

    response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random")
    if response.status_code == 200:
        fact = response.json().get('text')
        return fact
    else:
        return "Failed to get inspiration"


if __name__ == "__main__":
    # Example usage
    query = "appPle"
    choices = ["banana", "apple pie", "orange", "apple"]
    
    best_match = find_closest_match(query, choices)
    print(f"The best match for '{query}' is: '{best_match}'")