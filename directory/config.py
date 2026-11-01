"""Settings shared by the app and the migration script."""

APP_NAME = "Work and Travel Directory"
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
ENTITY_TYPES = {"employer": "Employer", "agency": "Recruitment agency"}

EMPLOYER_RATINGS = [
    "Pay", "Hours", "Housing", "Management", "Fair treatment",
    "Second-job access", "Transport",
]
AGENCY_RATINGS = ["Communication", "Honesty about the job", "Fees", "Support"]

ISSUE_CHIPS = [
    "No overtime", "Hours cut", "Low pay", "Tips withheld", "Poor housing",
    "Far from everything", "No second job", "Racism or discrimination",
    "Favouritism",
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

POSITION_GROUPS = {
    "Housekeeping": r"house\s?keep|room attendant",
    "Food & beverage": r"server|cook|busser|host|dish|kitchen|food|bartender|prep",
    "Front desk": r"front\s?desk",
    "Rides & attractions": r"ride|attendant|adventure",
    "Lifeguard": r"life\s?guard",
    "Retail & sales": r"retail|sales|store|shop|cashier|clerk",
}
