from thefuzz import process


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
        return "None"
    
    # extractOne returns a tuple: (best_match, score)
    best_match = process.extractOne(query, choices)[0]
    
    return best_match


if __name__ == "__main__":
    # Example usage
    query = "appPle"
    choices = ["banana", "apple pie", "orange", "apple"]
    
    best_match = find_closest_match(query, choices)
    print(f"The best match for '{query}' is: '{best_match}'")