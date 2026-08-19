def create_character(name, strength, intelligence, charisma):
    full_dot = '●'
    empty_dot = '○'

    # Name validation
    if not isinstance(name, str):
        return 'The character name should be a string'
    if len(name) == 0:
        return 'The character should have a name'
    if len(name) > 10:
        return 'The character name is too long'
    if ' ' in name:
        return 'The character name should not contain spaces'

    # Type validation for stats
    if not isinstance(strength, int) or type(strength) is bool or \
       not isinstance(intelligence, int) or type(intelligence) is bool or \
       not isinstance(charisma, int) or type(charisma) is bool:
        return 'All stats should be integers'

    # Value range validation
    if strength < 1 or intelligence < 1 or charisma < 1:
        return 'All stats should be no less than 1'
    if strength > 4 or intelligence > 4 or charisma > 4:
        return 'All stats should be no more than 4'

    # Point total validation
    if strength + intelligence + charisma != 7:
        return 'The character should start with 7 points'

    # Format output lines
    str_line = f"STR {full_dot * strength}{empty_dot * (10 - strength)}"
    int_line = f"INT {full_dot * intelligence}{empty_dot * (10 - intelligence)}"
    cha_line = f"CHA {full_dot * charisma}{empty_dot * (10 - charisma)}"

    return f"{name}\n{str_line}\n{int_line}\n{cha_line}"
