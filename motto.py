import os
import random


def motto(config):
    """
    从 motto 文件中随机选取格言
    """
    mottofile = config.motto["path"]
    if not os.path.exists(mottofile):
        return f"{mottofile} not found"
    with open(mottofile, "r") as f:
        lines = [
            line
            for line in f.readlines()
            if line.startswith(config.motto["prefix"])
        ]
    return random.sample(lines, config.motto["num"])
