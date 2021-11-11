import random


# noinspection PyPep8Naming
def randomNames(seed: int = None, count: int = 1) -> list[str]:
    names = (
        "Aardvark", "Alligator", "Alpaca", "Anaconda", "Antelope", "Ape", "Armadillo", "Baboon", "Badger", "Barracuda",
        "Bear", "Beaver", "Bird", "Bison", "Bluejay", "Bobcat", "Buffalo", "Butterfly", "Buzzard", "Camel", "Caribou",
        "Carp", "Cat", "Caterpillar", "Catfish", "Cheetah", "Chicken", "Chimpanzee", "Chipmunk", "Cobra", "Cod",
        "Condor", "Cougar", "Cow", "Coyote", "Crab", "Crane", "Cricket", "Crocodile", "Crow", "Deer", "Dinosaur", "Dog",
        "Dolphin", "Donkey", "Dove", "Dragonfly", "Duck", "Eagle", "Eel", "Elephant", "Emu", "Falcon", "Ferret",
        "Finch", "Flamingo", "Fox", "Frog", "Goat", "Goose", "Gopher", "Gorilla", "Grasshopper", "Hamster", "Hare",
        "Hawk", "Hippopotamus", "Horse", "Hummingbird", "Husky", "Iguana", "Impala", "Kangaroo", "Ladybug", "Leopard",
        "Lion", "Lizard", "Llama", "Lobster", "Mongoose", "Monkey", "Moose", "Mule", "Octopus", "Orca", "Ostrich",
        "Otter", "Owl", "Ox", "Oyster", "Panda", "Panther", "Parrot", "Peacock", "Pelican", "Penguin", "Perch",
        "Pheasant", "Pig", "Pigeon", "Porcupine", "Quail", "Rabbit", "Raccoon", "Rattlesnake", "Raven", "Rooster",
        "Sealion", "Sheep", "Skunk", "Snail", "Snake", "Tiger", "Walrus", "Whale", "Wolf", "Zebra"
    )
    random.seed(seed)
    return random.sample(names, count)
