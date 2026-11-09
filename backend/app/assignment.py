from app.models import User


def pick_officer(officers: list[User], open_loans: dict[int, int]) -> User:
    """Officer in the branch with the fewest open loans; lowest id breaks ties."""
    return min(officers, key=lambda o: (open_loans.get(o.id, 0), o.id))
