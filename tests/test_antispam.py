"""Tests for anti-spam and activity reward calculations."""
import pytest
from pvp2.balance import calculate_message_rewards, MIN_MESSAGE_LENGTH


class TestAntiSpam:
    def test_short_message_no_reward(self):
        """Messages shorter than MIN_MESSAGE_LENGTH get 0 XP, 0 gold."""
        xp, gold = calculate_message_rewards(message_length=2, unique_words=1)
        assert xp == 0
        assert gold == 0

    def test_3_char_message_no_reward(self):
        """3-character messages should still be below threshold."""
        xp, gold = calculate_message_rewards(message_length=3, unique_words=1)
        assert xp == 0
        assert gold == 0

    def test_7_char_below_threshold(self):
        """7 chars is still below MIN_MESSAGE_LENGTH (8)."""
        xp, gold = calculate_message_rewards(message_length=7, unique_words=2)
        assert xp == 0
        assert gold == 0

    def test_exactly_min_length_gets_reward(self):
        """Message at exactly MIN_MESSAGE_LENGTH should get some reward."""
        xp, gold = calculate_message_rewards(message_length=MIN_MESSAGE_LENGTH, unique_words=2)
        assert xp > 0
        assert gold > 0

    def test_longer_message_more_reward(self):
        """Longer, more varied messages should earn more."""
        short_xp, short_gold = calculate_message_rewards(message_length=10, unique_words=2)
        long_xp, long_gold = calculate_message_rewards(message_length=50, unique_words=10)
        assert long_xp >= short_xp
        assert long_gold >= short_gold

    def test_reward_caps_exist(self):
        """Even very long messages should be capped."""
        from pvp2.balance import MAX_XP_PER_MESSAGE, MAX_GOLD_PER_MESSAGE
        xp, gold = calculate_message_rewards(message_length=10000, unique_words=500)
        assert xp <= MAX_XP_PER_MESSAGE * 3  # allow prestige bonus room
        assert gold <= MAX_GOLD_PER_MESSAGE * 3

    def test_unique_words_matter(self):
        """Same length but more unique words should give more (or equal) XP."""
        xp_low, _ = calculate_message_rewards(message_length=30, unique_words=2)
        xp_high, _ = calculate_message_rewards(message_length=30, unique_words=8)
        assert xp_high >= xp_low

    def test_spam_single_word_repeated(self):
        """Repeating a single word (low unique_words) shouldn't max rewards."""
        from pvp2.balance import MAX_XP_PER_MESSAGE
        # "hi hi hi hi hi hi hi hi hi hi" = 30 chars, 1 unique word
        xp, gold = calculate_message_rewards(message_length=30, unique_words=1)
        assert xp < MAX_XP_PER_MESSAGE

    def test_prestige_bonus_applied(self):
        """Prestige tier should increase rewards."""
        xp_base, gold_base = calculate_message_rewards(message_length=30, unique_words=5, prestige_tier=0)
        xp_pres, gold_pres = calculate_message_rewards(message_length=30, unique_words=5, prestige_tier=1)
        assert xp_pres > xp_base
        assert gold_pres > gold_base

    def test_high_prestige_bigger_bonus(self):
        """Higher prestige tiers should give bigger bonuses."""
        _, gold_t1 = calculate_message_rewards(message_length=30, unique_words=5, prestige_tier=1)
        _, gold_t3 = calculate_message_rewards(message_length=30, unique_words=5, prestige_tier=3)
        assert gold_t3 > gold_t1
