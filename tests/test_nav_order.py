"""
tests/test_nav_order.py
Per-user sidebar order: the nav_order column is added by migration, defaults to
NULL, and round-trips as a comma-separated id string.
"""


class TestNavOrderStorage:
    def test_column_defaults_to_none(self, db, user_id):
        assert db.get_user(user_id)["nav_order"] is None

    def test_round_trips(self, db, user_id):
        order = "5,1,0,2,3,4,6,7,8,9,10,11,12,13"
        db.update_user_nav_order(user_id, order)
        assert db.get_user(user_id)["nav_order"] == order

    def test_overwrites_previous_order(self, db, user_id):
        db.update_user_nav_order(user_id, "1,0")
        db.update_user_nav_order(user_id, "0,1")
        assert db.get_user(user_id)["nav_order"] == "0,1"
