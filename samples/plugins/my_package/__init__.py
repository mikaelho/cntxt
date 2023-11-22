from cntxt import cntxt


def core_function() -> list[str]:
    result = ["main"]

    for plugin in cntxt["plugins"]:
        result.append(plugin())

    return result
