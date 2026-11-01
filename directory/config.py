"""Settings shared by the app and the migration script."""

APP_NAME = "Work and Travel Directory"
APP_HEADLINE = "Know the job before you fly."
APP_TAGLINE = "Reported experiences from J-1 Work & Travel participants, searchable in one place."
OPERATOR_NAME = "the volunteers who run this directory"

DATA_TTL_SECONDS = 300
FETCH_TIMEOUT_SECONDS = 10
SUBMIT_TIMEOUT_SECONDS = 30
RETRY_COOLDOWN_SECONDS = 60
REFRESH_COOLDOWN_SECONDS = 60
PAGE_SIZE = 20
EXCERPT_LENGTH = 220

# The app loads these columns and nothing else, so a stray column added to the
# public sheet can never reach a visitor.
PUBLIC_COLUMNS = [
    "record_id",
    "employer_name",
    "entity_type",
    "state",
    "city",
    "position",
    "report_description",
    "ratings",
    "experience_period",
    "submission_type",
    "date_reported",
    "last_updated",
    "verification_status",
    "review_state",
    "source",
]
REQUIRED_VALUES = ["record_id", "employer_name", "report_description"]

MULTIPLE_STATES = "Multiple states"
ALL_POSITIONS = "All positions"
NOT_STATED = "Not stated"
EMPLOYER_NOT_NAMED = "Employer not named"
NO_DETAILS_TEXT = "Listed in the 2026 community spreadsheet with no details given."
REDACTION_MARKER = "[removed by moderators]"
SOURCE_LEGACY = "Community list 2026"
SOURCE_FORM = "Website form"
LIST_NAME = "Jobs to Avoid"

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]

# The tile map: each state's abbreviation, row and column on an 11 by 8 grid.
STATE_TILES = {
    "Alaska": ("AK", 0, 0), "Maine": ("ME", 0, 10),
    "Wisconsin": ("WI", 1, 5), "Vermont": ("VT", 1, 9), "New Hampshire": ("NH", 1, 10),
    "Washington": ("WA", 2, 0), "Idaho": ("ID", 2, 1), "Montana": ("MT", 2, 2),
    "North Dakota": ("ND", 2, 3), "Minnesota": ("MN", 2, 4), "Illinois": ("IL", 2, 5),
    "Michigan": ("MI", 2, 6), "New York": ("NY", 2, 8), "Massachusetts": ("MA", 2, 9),
    "Oregon": ("OR", 3, 0), "Nevada": ("NV", 3, 1), "Wyoming": ("WY", 3, 2),
    "South Dakota": ("SD", 3, 3), "Iowa": ("IA", 3, 4), "Indiana": ("IN", 3, 5),
    "Ohio": ("OH", 3, 6), "Pennsylvania": ("PA", 3, 7), "New Jersey": ("NJ", 3, 8),
    "Connecticut": ("CT", 3, 9), "Rhode Island": ("RI", 3, 10),
    "California": ("CA", 4, 0), "Utah": ("UT", 4, 1), "Colorado": ("CO", 4, 2),
    "Nebraska": ("NE", 4, 3), "Missouri": ("MO", 4, 4), "Kentucky": ("KY", 4, 5),
    "West Virginia": ("WV", 4, 6), "Virginia": ("VA", 4, 7), "Maryland": ("MD", 4, 8),
    "Delaware": ("DE", 4, 9),
    "Arizona": ("AZ", 5, 1), "New Mexico": ("NM", 5, 2), "Kansas": ("KS", 5, 3),
    "Arkansas": ("AR", 5, 4), "Tennessee": ("TN", 5, 5), "North Carolina": ("NC", 5, 6),
    "South Carolina": ("SC", 5, 7), "District of Columbia": ("DC", 5, 8),
    "Oklahoma": ("OK", 6, 3), "Louisiana": ("LA", 6, 4), "Mississippi": ("MS", 6, 5),
    "Alabama": ("AL", 6, 6), "Georgia": ("GA", 6, 7),
    "Hawaii": ("HI", 7, 0), "Texas": ("TX", 7, 3), "Florida": ("FL", 7, 8),
}

UNVERIFIED = "unverified"
VERIFICATION_LABELS = {
    "community_reported": (
        "Community-reported",
        "One person's account. It has not been independently checked.",
    ),
    "multiple_reports": (
        "Multiple reports",
        "More than one separately written account. These have not been independently checked.",
    ),
    "verified": (
        "Independently verified",
        "Confirmed by moderators against a public source.",
    ),
    UNVERIFIED: (
        "Not verified",
        "The origin or accuracy of this information is unknown.",
    ),
}

SUBMISSION_TYPES = {
    "report": "Report",
    "review": "Review",
    "job_opportunity": "Job opportunity",
}
SUBMISSION_ICONS = {
    "report": ":material/flag:",
    "review": ":material/star:",
    "job_opportunity": ":material/work:",
}
ENTITY_TYPES = {"employer": "Employer", "agency": "Recruitment agency"}

EMPLOYER_RATINGS = [
    "Pay", "Hours", "Housing", "Management", "Fair treatment",
    "Second-job access", "Transport",
]
AGENCY_RATINGS = ["Communication", "Honesty about the job", "Fees", "Support"]

# Visitors choose good, neutral or bad, kept in the ratings column as `Overall=good`
# and shown as a badge. The imported list has no ratings, so its records only
# mention where the data was pulled from, in words that are never the site's own
# verdict and in plain text rather than a badge.
OVERALL_RATING = "Overall"
OVERALL_CHOICES = ["good", "neutral", "bad"]
FROM_LIST = "list"
WRITER_CHOSE = "The person who wrote this chose that rating. It isn't the directory's view."
EXPERIENCE_LABELS = {
    "good": ("Good experience", WRITER_CHOSE),
    "neutral": ("Neutral experience", WRITER_CHOSE),
    "bad": ("Bad experience", WRITER_CHOSE),
    FROM_LIST: (
        f"Data pulled from the {LIST_NAME} list",
        f"The {LIST_NAME} list is a spreadsheet shared in the community in 2026. It has no ratings.",
    ),
}
EXPERIENCE_ICONS = {
    "good": ":material/sentiment_satisfied:",
    "neutral": ":material/sentiment_neutral:",
    "bad": ":material/sentiment_dissatisfied:",
    FROM_LIST: ":material/list_alt:",
}

ISSUE_CHIPS = [
    "No overtime", "Hours cut", "Low pay", "Tips withheld", "Poor housing",
    "Far from everything", "No second job", "Racism or discrimination",
    "Favouritism",
]
GOOD_CHIPS = [
    "Overtime available", "Steady hours", "Good pay", "Fair tips", "Good housing",
    "Close to everything", "Second job allowed", "Treated with respect",
    "Fair management",
]
COMMON_POSITIONS = [
    ALL_POSITIONS, "Housekeeping", "Server", "Line cook", "Food service",
    "Front desk", "Ride operator", "Lifeguard", "Retail sales",
]

# "Reports mention" filters. These describe a report's subject, never a verdict,
# which is why there is deliberately no "safety" topic.
TOPICS = {
    "Hours": r"\bhours?\b|\bhrs?\b",
    "Pay": r"\bpay\b|\bpaid\b|\bwage|\brate\b|\btips?\b",
    "Management": r"manage|\bboss|supervisor|\bemployer",
    "Discrimination": r"racis|discriminat|prejudic|favou?rit|(hate|like) jamaican",
    "Second job": r"(second|2nd) job",
    "Overtime": r"over\s?time|\bOT\b",
    "Housing": r"housing|\bdorm|apartment|accommodation",
    "Transport": r"transport|\buber\b|\btaxi\b|\bbus\b|far from|far away",
}
TOPIC_ICONS = {
    "Hours": ":material/schedule:",
    "Pay": ":material/payments:",
    "Management": ":material/supervisor_account:",
    "Discrimination": ":material/front_hand:",
    "Second job": ":material/work_history:",
    "Overtime": ":material/more_time:",
    "Housing": ":material/home:",
    "Transport": ":material/directions_bus:",
}

POSITION_GROUPS = {
    "Housekeeping": r"house\s?keep|room attendant",
    "Food & beverage": r"server|cook|busser|host|dish|kitchen|food|bartender|prep",
    "Front desk": r"front\s?desk",
    "Rides & attractions": r"ride|attendant|adventure",
    "Lifeguard": r"life\s?guard",
    "Retail & sales": r"retail|sales|store|shop|cashier|clerk",
}
