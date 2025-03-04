import pygame, random, sys, openai
from utils import create_deck, distribute_cards

pygame.init()

API_KEY = ""
openai.api_key = API_KEY

# --- LLM Player Class ---
class LLM_player:
    def __init__(self, api_key, cards=None):
        if cards is None:
            cards = {'A': 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        self.cards = cards
        self.api_key = api_key
        self.initial_prompt = """
You are an AI that play the game card game BS. In this game there are 7 cards (A, 2, 3, 4, 5, 6, 7), 3 players including you (P1, P2, P3), you are P1, there are only 6 cards of each type, cards are randomly distributed and each player gets the same amount of cards.
You are P1. The game is as follows:
- Each turn has a specific card type, for example, A.
- Players take turns to place however many cards they want, face down (other players cannot see them).
- They can lie and say the cards they played is the type of the turn but it might not be. For example, if the turn was A, he could lie and place 3 cards of type 2 or tell the truth and play 1 of A.
- Each turn the remaining players can check (do nothing) or call the bluff.
- 4 possible outcomes here:
  a) actor was bluffing, gets called: pile gets split among actor and non-callers
  b) actor was honest, gets called: pile gets split among callers
  c) actor was honest, no callers: nothing happens, pile grows
  d) actor was bluffing, no callers: pile is split among non-callers (player has “bluffed everyone out”)
- A player wins whenever he has five or less total cards.

Your goal is to win the game using the following information:
- Total amount of cards per player.
- Number of times the player has bluffed.
- Number of times the player has been honest.

You need to think step by step.

Answer in the format:
  if it is your turn:
    Step 1: ...
    Step 2: ...
    Step 3: ...
    Step 4: ...
    Answer: {number of cards} {bluff or real}
  if it is not your turn:
    Step 1: ...
    Step 2: ...
    Step 3: ...
    Step 4: ...
    Answer: {check or bluff}

Use the examples provided below.
Q1: Is not your turn. Your available cards are {'A': 2, 2: 0, 3: 1, 4: 0, 5: 3, 6: 1, 7: 4}

  P2 Information:
    Total cards: 13
    Bluffed times: 2
    Honest: 1

  P3 Information:
    Total cards: 18
    Bluffed times: 0
    Honest: 3

  Round card type is 4, P2 claims to have 3 cards of type 4.
A1:
  Step 1: P2 has bluffed more times than he has being honest.
  Step 2: P2 still has 13 cards, he could have 3 cards of type 4.
  Step 3: I do not have any cards of type 4, is probable that he has 3.
  Step 4: It is probable for him those cards.
  Answer: check

Q2: Is not your turn. Your available cards are {'A': 4, 2: 0, 3: 1, 4: 0, 5: 3, 6: 1, 7: 4}

  P2 Information:
    Total cards: 20
    Bluffed times: 2
    Honest: 1

  P3 Information:
    Total cards: 10
    Bluffed times: 3
    Honest: 3

  Round card type is A, P3 claims to have 3 cards of type A.
A2:
  Step 1: P3 has not bluffed more than he has being honest.
  Step 2: P3 still has 10 cards, he could have 3 cards of type A.
  Step 3: I have 4 cards of type A, is not probable for him to have 3 cards of type A.
  Step 4: 3 + 4 = 7, maximum amount the cards is 6.
  Answer: bluff

Q3: Is not your turn. Your available cards are {'A': 4, 2: 4, 3: 1, 4: 0, 5: 1, 6: 1, 7: 5}

  P2 Information:
    Total cards: 16
    Bluffed times: 10
    Honest: 1

  P3 Information:
    Total cards: 10
    Bluffed times: 11
    Honest: 0

  Round card type is 7, P3 claims to have 1 card of type 7.
A3:
  Step 1: P3 has only bluffed.
  Step 2: P3 still has 16 cards, he could have 1 cards of type A.
  Step 3: I have 5 cards of type A, is possible for him to have 1 card of type A.
  Step 4: He has only bluffed, he must be bluffing again.
  Answer: bluff

Q4: Is your turn. Your available cards are {'A': 3, 2: 2, 3: 1, 4: 2, 5: 1, 6: 1, 7: 2}

  P2 Information:
    Total cards: 6
    Bluffed times: 10
    Honest: 1

  P3 Information:
    Total cards: 24
    Bluffed times: 0
    Honest: 11

  Round card type is 2, is your time to place cards, answer in the format {number of cards} {bluff or real}.
A4:
  Step 1: I have 3 + 2 + 1 + 2 + 1 + 2 = 12 cards.
  Step 2: I do not have a large amount of type 2 cards.
  Step 3: P2 is close to win.
  Step 4: I need to bluff to get rid of cards.
  Answer: 4 bluff

Q5: Is your turn. Your available cards are {'A': 0, 2: 2, 3: 1, 4: 2, 5: 0, 6: 1, 7: 1}

  P2 Information:
    Total cards: 6
    Bluffed times: 10
    Honest: 1

  P3 Information:
    Total cards: 10
    Bluffed times: 0
    Honest: 11

  Round card type is 4, is your time to place cards, answer in the format {number of cards} {bluff or real}.
A5:
  Step 1: I have 0 + 2 + 1 + 2 + 1 + 1 = 7 cards.
  Step 2: 2 cards of type 4 is enough to win.
  Step 3: P2 is close to win.
  Step 4: Telling the truth is enoug to win.
  Answer: 2 real
"""
    def call_chatgpt(self, conversation_history):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=conversation_history,
                max_tokens=150,
                temperature=0.7,
            )
            reply = response["choices"][0]["message"]["content"].strip()
            return reply
        except Exception as e:
            print("LLM API error:", e)
            return "Step 1: ... Step 2: ... Step 3: ... Step 4: ... Answer: 1 real"
    def play(self, p2_total, p2_bluffs, p2_honest, p3_total, p3_bluffs, p3_honest, round_card, player_turn, player_claim=None):
        if player_turn != "GPT":
            prompt = f"""Is not your turn. Your available cards are {self.cards}

P2 Information:
  Total cards: {p2_total}
  Bluffed times: {p2_bluffs}
  Honest: {p2_honest}

P3 Information:
  Total cards: {p3_total}
  Bluffed times: {p3_bluffs}
  Honest: {p3_honest}

Round card type is {round_card}, {player_turn} claims to have {player_claim} card(s) of type {round_card}."""
        else:
            prompt = f"""It is your turn. Your available cards are {self.cards}

P2 Information:
  Total cards: {p2_total}
  Bluffed times: {p2_bluffs}
  Honest: {p2_honest}

P3 Information:
  Total cards: {p3_total}
  Bluffed times: {p3_bluffs}
  Honest: {p3_honest}

Round card type is {round_card}. It is your turn to play. Answer in the format: 
  Step 1: ...
  Step 2: ...
  Step 3: ...
  Step 4: ...
  Answer: <number> <bluff or real>"""
        conversation_history = [{"role": "system", "content": self.initial_prompt},
                                {"role": "user", "content": prompt}]
        print("LLM Prompt:", prompt)
        response = self.call_chatgpt(conversation_history)
        return response

# Create an instance of LLM_player for "GPT".
llm_player = LLM_player(API_KEY)
# Create a very small font for displaying CoT reasoning.
cot_font = pygame.font.Font("Minecraft.ttf", 12)

# --- Pygame Setup ---
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("5 Or Less")

GREEN = (0, 128, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
CARD_BACK_COLOR = (0, 0, 100)

font = pygame.font.Font("PressStart2P.ttf", 25)
font_small = pygame.font.Font("Minecraft.ttf", 20)
pile_font = pygame.font.Font("Minecraft.ttf", 40)
claim_font = pygame.font.Font("PressStart2P.ttf", 15)

RANKS = ["A", "2", "3", "4", "5", "6", "7"]
user = "You"

player_positions = {
    user: (WIDTH // 2, HEIGHT - 100),
    "GTO": (100, 100),
    "GPT": (WIDTH - 100, 100)
}

deck = create_deck()
player_hands = distribute_cards(deck, player_positions)

selected_indices = set()
pile = []
claim_msg = ""

turn_order = [user, "GTO", "GPT"]
current_turn_index = 0
current_rank_index = 0
call_phase = False

last_played = []
last_claimant = None
call_decisions = {}

highlight_duration = 2000
play_pressed_time = None
call_pressed_time = None
no_call_pressed_time = None

call_resolved_time = None
call_resolution_delay = 3000

clock = pygame.time.Clock()
running = True

button_width, button_height = 100, 40
button_x = player_positions[user][0] + 60 
button_y = player_positions[user][1] - 20
play_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
call_button_rect = pygame.Rect(button_x + button_width + 10, button_y, button_width, button_height)
no_call_button_rect = pygame.Rect(button_x + 2 * (button_width + 10), button_y, button_width, button_height)

def draw_button(rect, text, pressed_time):
    current_time = pygame.time.get_ticks()
    color = (200, 200, 200) if pressed_time and current_time - pressed_time < highlight_duration else GRAY
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, BLACK, rect, 2)
    text_surface = font_small.render(text, True, BLACK)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)

def bot_move(bot_name):
    hand = player_hands[bot_name]
    if not hand:
        return f"{bot_name} has no cards left.", []
    if bot_name == "GTO":
        card = random.choice(hand)
        count = hand.count(card)
        play_count = random.randint(1, count)
        selected_cards = []
        for _ in range(play_count):
            hand.remove(card)
            selected_cards.append(card)
        for c in selected_cards:
            pile.append(c)
        return f"{bot_name} claims to play {play_count} cards of {RANKS[current_rank_index]}", selected_cards
    else:
        p2_total = len(player_hands["GTO"])
        p2_bluffs = 0
        p2_honest = 0
        p3_total = len(player_hands["GPT"])
        p3_bluffs = 0
        p3_honest = 0
        round_card = RANKS[current_rank_index]
        llm_response = llm_player.play(p2_total, p2_bluffs, p2_honest, p3_total, p3_bluffs, p3_honest,
                                       round_card, "GPT")
        global llm_cot_reasoning_global
        try:
            parts = llm_response.split("Answer:")
            llm_cot_reasoning_global = parts[0].strip()
            final_answer = parts[1].strip()  # e.g., "2 bluff" or "3 real"
            num_cards = int(final_answer.split()[0])
        except Exception as e:
            print("LLM parsing error:", e)
            llm_cot_reasoning_global = ""
            num_cards = 1
            final_answer = "1 real"
        selected_cards = []
        available = hand[:]
        random.shuffle(available)
        num_cards = min(num_cards, len(available))
        for _ in range(num_cards):
            card = available.pop()
            hand.remove(card)
            selected_cards.append(card)
            pile.append(card)
        claim_str = f"GPT claims to play {num_cards} cards of {round_card}"
        return claim_str, selected_cards, llm_cot_reasoning_global

def bot_call_decision(bot_name):
    return random.random() < 0.3

def collect_call_decisions():
    for p in turn_order:
        if p != last_claimant and p not in call_decisions:
            if p != user:
                call_decisions[p] = bot_call_decision(p)
    return len(call_decisions) == (len(turn_order) - 1)

def split_pile_among(players_list):
    global pile, player_hands
    if not pile:
        return
    pile_copy = pile[:]
    random.shuffle(pile_copy)
    pile_size = len(pile_copy)
    n = len(players_list)
    share_size = pile_size // n
    remainder = pile_size % n
    index = 0
    for p in players_list:
        for _ in range(share_size):
            player_hands[p].append(pile_copy[index])
            index += 1
    random.shuffle(players_list)
    for i in range(remainder):
        p = players_list[i]
        player_hands[p].append(pile_copy[index])
        index += 1
    pile.clear()

def resolve_call():
    global last_played, call_decisions, last_claimant, current_rank_index
    bluff = any(card != current_rank_index for card in last_played)
    any_called = any(decision for decision in call_decisions.values())
    if bluff:
        if not any_called:
            non_callers = [p for p in turn_order if p != last_claimant and call_decisions.get(p) == False]
            if non_callers:
                split_pile_among(non_callers)
            outcome = "Bluff detected, no one called. Pile split among non-callers."
        else:
            punished = [last_claimant] + [p for p in turn_order if p != last_claimant and call_decisions.get(p) == False]
            split_pile_among(punished)
            outcome = "Bluff detected! Claimant and non-callers take the pile."
    else:
        if not any_called:
            outcome = "Truthful play, no calls. Pile remains."
        else:
            callers = [p for p, decision in call_decisions.items() if decision]
            split_pile_among(callers)
            outcome = "Truthful play, but call was made. Callers take the pile."
    last_played.clear()
    last_claimant = None
    return outcome

llm_cot_reasoning_global = ""  # Global variable for storing GPT's CoT reasoning.

# --- Main Loop ---
while running:
    player_hands[user].sort()
    user_hand = player_hands[user]
    card_w, card_h = 60, 90
    x_offset = WIDTH // 2 - (len(user_hand) * (card_w + 5)) // 2 
    y_position = HEIGHT - 250
    card_rects = []
    for idx, card in enumerate(user_hand):
        rect = pygame.Rect(x_offset, y_position, card_w, card_h)
        card_rects.append((rect, idx))
        x_offset += card_w + 5

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            if call_phase:
                if user not in call_decisions:
                    if call_button_rect.collidepoint(mouse_pos):
                        call_pressed_time = pygame.time.get_ticks()
                        call_decisions[user] = True
                    elif no_call_button_rect.collidepoint(mouse_pos):
                        no_call_pressed_time = pygame.time.get_ticks()
                        call_decisions[user] = False
            else:
                current_player = turn_order[current_turn_index]
                if current_player == user:
                    if play_button_rect.collidepoint(mouse_pos):
                        play_pressed_time = pygame.time.get_ticks()
                        if selected_indices:
                            selected_cards = [user_hand[i] for i in sorted(selected_indices)]
                            claim_msg = f"You claim to play {len(selected_cards)} cards of {RANKS[current_rank_index]}"
                            for idx in sorted(selected_indices, reverse=True):
                                card = user_hand.pop(idx)
                                pile.append(card)
                            selected_indices.clear()
                            last_played = selected_cards[:]
                            last_claimant = user
                            call_phase = True
                            call_decisions = {}
                    else:
                        for rect, idx in card_rects:
                            if rect.collidepoint(mouse_pos):
                                if idx in selected_indices:
                                    selected_indices.remove(idx)
                                else:
                                    selected_indices.add(idx)
                                break

    if call_phase:
        if collect_call_decisions():
            if last_claimant == "GPT":
                if call_resolved_time is None:
                    call_resolved_time = pygame.time.get_ticks()
                elif pygame.time.get_ticks() - call_resolved_time >= call_resolution_delay:
                    outcome_msg = resolve_call()
                    claim_msg = outcome_msg
                    call_phase = False
                    call_resolved_time = pygame.time.get_ticks()
                    call_decisions.clear()
            else:
                outcome_msg = resolve_call()
                claim_msg = outcome_msg
                call_phase = False
                call_resolved_time = pygame.time.get_ticks()
                call_decisions.clear()

    if call_resolved_time and not call_phase and pygame.time.get_ticks() - call_resolved_time >= call_resolution_delay and last_claimant != "GPT":
        call_resolved_time = None
        current_turn_index = (current_turn_index + 1) % len(turn_order)
        current_rank_index = (current_rank_index + 1) % len(RANKS)

    current_player = turn_order[current_turn_index]
    if not call_phase and current_player != user and not call_resolved_time:
        if current_player == "GPT":
            p2_total = len(player_hands["GTO"])
            p2_bluffs = 0
            p2_honest = 0
            p3_total = len(player_hands["GPT"])
            p3_bluffs = 0
            p3_honest = 0
            round_card = RANKS[current_rank_index]
            llm_response = llm_player.play(p2_total, p2_bluffs, p2_honest, p3_total, p3_bluffs, p3_honest,
                                           round_card, "GPT")
            try:
                parts = llm_response.split("Answer:")
                llm_cot_reasoning_global = parts[0].strip()
                final_answer = parts[1].strip()  # e.g., "2 bluff" or "3 real"
                num_cards = int(final_answer.split()[0])
            except Exception as e:
                print("LLM parsing error:", e)
                llm_cot_reasoning_global = ""
                num_cards = 1
                final_answer = "1 real"
            hand = player_hands["GPT"]
            available = hand[:]
            random.shuffle(available)
            num_cards = min(num_cards, len(available))
            selected_cards = []
            for _ in range(num_cards):
                card = available.pop()
                hand.remove(card)
                selected_cards.append(card)
                pile.append(card)
            claim_msg = f"GPT claims to play {num_cards} cards of {round_card}"
            last_played = selected_cards[:]
            last_claimant = "GPT"
            call_phase = True
            call_decisions = {}
        else:
            msg, played = bot_move(current_player)
            claim_msg = msg
            last_played = played[:]
            last_claimant = current_player
            call_phase = True
            call_decisions = {}

    screen.fill(GREEN)
    
    current_turn_text = font_small.render(f"Current Turn: {RANKS[current_rank_index]}", True, WHITE)
    current_turn_rect = current_turn_text.get_rect(center=(WIDTH//2, 30))
    screen.blit(current_turn_text, current_turn_rect)
    
    for name, pos in player_positions.items():
        circle_color = YELLOW if name == turn_order[current_turn_index] else WHITE
        pygame.draw.circle(screen, circle_color, pos, 40)
        ts = font.render(name, True, BLACK)
        tr = ts.get_rect(center=pos)
        screen.blit(ts, tr)
    
    for p in turn_order:
        if p != last_claimant and p in call_decisions:
            decision_str = "Call" if call_decisions[p] else "No Call"
            pos = player_positions[p]
            offset = (0, 100) if pos[1] < HEIGHT/2 else (0, -100)
            dt = font_small.render(decision_str, True, BLACK)
            dr = dt.get_rect(center=(pos[0] + offset[0], pos[1] + offset[1]))
            screen.blit(dt, dr)
    
    for name in ["GTO", "GPT"]:
        count = len(player_hands[name])
        ts = font_small.render(f"#: {count} cards", True, WHITE)
        pos = player_positions[name]
        tr = ts.get_rect(center=(pos[0], pos[1] + 60))
        screen.blit(ts, tr)
    
    user_count = len(player_hands[user])
    user_count_text = font_small.render(f"#: {user_count} cards", True, WHITE)
    user_count_rect = user_count_text.get_rect(topleft=(10, HEIGHT - 40))
    screen.blit(user_count_text, user_count_rect)
    
    x_offset = WIDTH // 2 - (len(user_hand) * (card_w + 5)) // 2
    y_position = HEIGHT - 250
    for idx, card in enumerate(user_hand):
        rect = pygame.Rect(x_offset, y_position, card_w, card_h)
        pygame.draw.rect(screen, WHITE, rect)
        pygame.draw.rect(screen, BLACK, rect, 2)
        if idx in selected_indices:
            pygame.draw.rect(screen, (255, 255, 0), rect, 3)
        ts = font_small.render(RANKS[card], True, BLACK)
        tr = ts.get_rect(center=rect.center)
        screen.blit(ts, tr)
        x_offset += card_w + 5
    
    pile_radius = 90
    pile_x = WIDTH // 2
    pile_y = HEIGHT // 2 - 75
    pygame.draw.circle(screen, CARD_BACK_COLOR, (pile_x, pile_y), pile_radius)
    pygame.draw.circle(screen, BLACK, (pile_x, pile_y), pile_radius, 2)
    pile_count = len(pile)
    pt = pile_font.render(str(pile_count), True, WHITE)
    tr = pt.get_rect(center=(pile_x, pile_y))
    screen.blit(pt, tr)
    
    if claim_msg:
        cs = claim_font.render(claim_msg, True, WHITE)
        cr = cs.get_rect(center=(WIDTH//2, HEIGHT//2 - 200))
        screen.blit(cs, cr)
    
    # Display GPT's chain-of-thought reasoning under its circle,
    # but only after both other players have made their call decision.
    if last_claimant == "GPT" and call_resolved_time is not None:
        # Display reasoning below GPT's circle, even lower.
        pos = player_positions["GPT"]
        cot_x = pos[0]
        cot_y = pos[1] + 80  # Increased offset (80 pixels below)
        for line in llm_cot_reasoning_global.split("\n"):
            # Ensure the text is white.
            line_surface = cot_font.render(line, True, WHITE)
            line_rect = line_surface.get_rect(center=(cot_x, cot_y))
            # If the line runs too far, wrap it (simple approach: truncate)
            if line_rect.width > 200:
                line_surface = cot_font.render(line[:30] + "...", True, WHITE)
                line_rect = line_surface.get_rect(center=(cot_x, cot_y))
            screen.blit(line_surface, line_rect)
            cot_y += line_rect.height + 2

    if not call_phase and turn_order[current_turn_index] == user:
        draw_button(play_button_rect, "Play", play_pressed_time)
    if call_phase and user not in call_decisions:
        draw_button(call_button_rect, "Call", call_pressed_time)
        draw_button(no_call_button_rect, "No Call", no_call_pressed_time)
    
    pygame.display.flip()
    clock.tick(60)
    
    winner = None
    for p in turn_order:
        if len(player_hands[p]) <= 5:
            winner = p
            break
    if winner is not None:
        claim_msg = f"Game Over: {winner} won!"
        screen.fill(GREEN)
        gs = claim_font.render(claim_msg, True, WHITE)
        gr = gs.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(gs, gr)
        pygame.display.flip()
        pygame.time.delay(3000)
        running = False

pygame.quit()
sys.exit()
