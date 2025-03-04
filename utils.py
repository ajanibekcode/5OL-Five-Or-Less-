import random

def create_deck():
    """Create a deck of 42 cards with 6 cards for each of the 7 types."""
    deck = []
    for rank in range(7):  # 0 to 6 representing A, 2, 3, 4, 5, 6, 7
        deck.extend([rank] * 6)
    random.shuffle(deck)
    return deck

def distribute_cards(deck, player_positions):
    """Distribute the deck of cards evenly among the players."""
    num_players = len(player_positions)
    player_hands = {player: [] for player in player_positions}
    
    for i, card in enumerate(deck):
        player = list(player_positions.keys())[i % num_players]
        player_hands[player].append(card)
    
    return player_hands

