from utils import greet
from dead import forgotten  # imported but never called: still live, see README
from pkg import api


def main():
    greet("world")
    api()


if __name__ == "__main__":
    main()
