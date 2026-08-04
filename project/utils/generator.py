import string
import secrets

def generate_string(
        length:int=16,
        digits: bool=False,
        lowercase: bool=False,
        uppercase: bool=False,
        symbols: bool=False,
):

    character_sets = {
        "digits": string.digits if digits else "",
        "lowercase": string.ascii_lowercase if lowercase else "",
        "uppercase": string.ascii_uppercase if uppercase else "",
        "symbols": string.punctuation if symbols else "",
    }

    character_pool = ''.join(character_sets.values())

    required_chars =[
        secrets.choice(charset)
        for charset in character_sets.values()
        if charset
    ]

    remaining_length = length - len(required_chars)
    if remaining_length > 0:
        required_chars += [
            secrets.choice(character_pool)
            for _ in range(remaining_length)
        ]

    for i in range(len(required_chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        required_chars[i], required_chars[j] = required_chars[j], required_chars[i]

    return "".join(required_chars)