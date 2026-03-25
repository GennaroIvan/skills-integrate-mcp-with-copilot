"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import time
from uuid import uuid4
from pydantic import BaseModel
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


TOKEN_TTL_SECONDS = 3600  # tokens expire after 1 hour


def _hash_password(password: str, salt: str) -> str:
    """Return PBKDF2-HMAC-SHA256 hex digest for *password* using hex *salt*."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), 260000
    ).hex()


def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """Constant-time password verification."""
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


# Passwords are stored as PBKDF2-HMAC-SHA256 hashes (salt + hash as hex strings).
users = {
    "student@mergington.edu": {
        "password_salt": "c09b1a37eadd5fd18980074c95712756",
        "password_hash": "d5ce7eb2dc686fd2925cfc2247c963d8bcdee12d7f48602b0026b94f8a67beae",
        "role": "student"
    },
    "admin@mergington.edu": {
        "password_salt": "c1059da05d6426fedd754edc53d6216e",
        "password_hash": "4ab19e04e25cce67d2267eb9fbda9ec8a587169543e5003992c72231008f3b9d",
        "role": "admin"
    }
}

# token -> {email: str, role: str, expires_at: float}
active_tokens: dict[str, dict[str, str | float]] = {}


class LoginRequest(BaseModel):
    email: str
    password: str


def get_current_user(authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = active_tokens.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if time.time() > user["expires_at"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def require_role(user: dict, allowed_roles: set[str]):
    if user["role"] not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action"
        )


def build_student_activities_view():
    result = {}
    for name, details in activities.items():
        result[name] = {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants_count": len(details["participants"])
        }
    return result


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/login")
def login(payload: LoginRequest):
    user = users.get(payload.email)
    if not user or not _verify_password(payload.password, user["password_salt"], user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = str(uuid4())
    active_tokens[token] = {
        "email": payload.email,
        "role": user["role"],
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "email": payload.email
    }


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@app.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    """Invalidate the current bearer token server-side."""
    if authorization:
        _, _, token = authorization.partition(" ")
        active_tokens.pop(token, None)
    return {"message": "Logged out successfully"}


@app.get("/activities")
def get_activities(user: dict = Depends(get_current_user)):
    require_role(user, {"student", "admin"})
    return build_student_activities_view()


@app.get("/admin/activities")
def get_admin_activities(user: dict = Depends(get_current_user)):
    require_role(user, {"admin"})
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, user: dict = Depends(get_current_user)):
    """Sign up a student for an activity"""
    require_role(user, {"student"})

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    email = user["email"]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, user: dict = Depends(get_current_user)):
    """Unregister a student from an activity"""
    require_role(user, {"admin"})

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
