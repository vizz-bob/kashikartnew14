from sqlalchemy.future import select
from sqlalchemy import and_
from dateutil.parser import parse
import re
from datetime import datetime

from app.models.excel_raw import ExcelRowRaw
from app.models.tender import Tender
from app.models.source import Source
from app.models.keyword import Keyword, TenderKeywordMatch


# ==================================================
# Utils
# ==================================================

def parse_date_safe(val):
    """Safely parse date from various formats"""
    if not val:
        return None
    try:
        return parse(str(val), fuzzy=True).date()
    except Exception:
        return None


def extract_any_date(data: dict):
    """Extract date from common date field names first, then any value"""
    date_fields = ['close date', 'deadline', 'due date', 'end date', 'close_date', 'broadcast date']

    # First check common date field names
    for key, val in data.items():
        key_lower = str(key).lower().strip()
        if any(df in key_lower for df in date_fields):
            d = parse_date_safe(val)
            if d:
                return d

    # Then check any value
    for v in data.values():
        d = parse_date_safe(v)
        if d:
            return d
    return None


def clean(v):
    """Clean and validate value"""
    if not v:
        return None
    s = str(v).strip()
    if s.upper() in ['N/A', 'NA', 'NONE', '']:
        return None
    return s


def normalize(v):
    """Normalize text for comparison"""
    if not v:
        return ""
    return re.sub(r"\s+", " ", str(v).lower()).strip()


# ==================================================
# Smart Detection Engine
# ==================================================

STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

# Enhanced reference pattern - covers all formats from your data
REF_PATTERN = re.compile(
    r'\b(RFP|RFQ|IFB|RFI|BID|IFB-|SS|AR|CS|DQ|CQ|NOA|RSQ|TRN|OPN|GEN|BLD|PRA|PNC|Draft|AD)\s*[-\s]?[A-Z0-9]{2,20}\b',
    re.IGNORECASE
)

AGENCY_WORDS = [
    "county", "city", "authority", "department", "district",
    "college", "university", "school", "tribe", "tribal",
    "port", "state", "board", "commission", "division",
    "municipality", "township", "government", "public works",
    "water", "sewer", "wastewater", "transportation", "engineering",
    "purchasing", "parks", "recreation", "facilities", "fasd", "sdot", "dep"
]

TITLE_INDICATORS = [
    "service", "project", "construction", "maintenance", "repair",
    "installation", "upgrade", "replacement", "design", "consulting",
    "management", "software", "equipment", "supply", "assessment",
    "improvement", "renovation", "monitoring", "study", "plan",
    "road", "bridge", "building", "facility", "system", "infrastructure"
]


# ==================================================
# Header Detection
# ==================================================

def detect_headers(data: dict):
    """Detect which keys are likely headers"""
    headers = {}

    for key in data.keys():
        key_lower = normalize(key)

        # Reference field detection
        if any(term in key_lower for term in ['ref', 'reference', 'oppid', 'projectid', 'number', 'solicitation']):
            headers['reference'] = key

        # Title/Project field detection
        elif any(term in key_lower for term in ['title', 'project', 'projectname', 'name']):
            if 'description' not in key_lower or len(key_lower) < 20:
                headers['title'] = key

        # Description field
        elif 'description' in key_lower:
            headers['description'] = key

        # Status field detection
        elif 'status' in key_lower and 'project' in key_lower:
            headers['status'] = key

        # Date field detection
        elif any(term in key_lower for term in ['closedate', 'deadline', 'duedate', 'enddate', 'opening']):
            headers['deadline'] = key
        elif any(term in key_lower for term in ['posted', 'broadcast', 'published']):
            headers['posted'] = key

        # Agency/Department field detection
        elif any(term in key_lower for term in ['department', 'agency', 'division', 'organization', 'cityagency']):
            headers['agency'] = key

        # Location field detection
        elif any(term in key_lower for term in ['location', 'district', 'county', 'state']):
            headers['location'] = key

        # Additional fields
        elif 'contact' in key_lower:
            headers['contact'] = key
        elif 'budget' in key_lower:
            headers['budget'] = key
        elif 'type' in key_lower:
            headers['type'] = key
        elif 'phase' in key_lower:
            headers['phase'] = key

    return headers


# ==================================================
# Validation
# ==================================================

def is_valid_ref(v):
    """Check if a value is a valid reference number"""
    if not v:
        return False

    # Block paragraphs
    if len(v) > 100:
        return False

    # Block multiline
    if "\n" in v:
        return False

    # Block long sentences
    if len(v.split()) > 8:
        return False

    # Must have some alphanumeric content
    if not re.search(r'[A-Z0-9]{2,}', str(v), re.IGNORECASE):
        return False

    return True


def is_valid_title(v):
    """Check if a value is a valid title"""
    if not v:
        return False

    # Too short
    if len(v) < 5:  # Reduced from 10 to catch shorter titles
        return False

    # Too long (likely a description)
    if len(v) > 500:
        return False

    # Block obvious non-titles (all caps paragraphs)
    if v.isupper() and len(v) > 100:
        return False

    return True


# ==================================================
# Scoring
# ==================================================

def score_title(v, key_hint=None):
    """Score how likely a value is to be a title"""
    score = 0
    v_lower = normalize(v)

    # Length scoring
    if 20 < len(v) < 200:
        score += 3
    elif 10 < len(v) <= 20:
        score += 2
    elif 5 < len(v) <= 10:
        score += 1
    elif len(v) > 200:
        score -= 3

    # Content scoring
    for indicator in TITLE_INDICATORS:
        if indicator in v_lower:
            score += 2

    # Has specific project indicators
    if any(term in v_lower for term in ['for', 'and', 'with', '-', '&']):
        score += 1

    # Penalty for all caps (unless short)
    if v.isupper() and len(v) > 50:
        score -= 2

    # Penalty for obvious reference numbers
    if REF_PATTERN.search(v):
        score -= 3

    # Key hint bonus
    if key_hint:
        key_norm = normalize(key_hint)
        if any(term in key_norm for term in ['title', 'project', 'name']):
            score += 5

    return score


def score_agency(v, key_hint=None):
    """Score how likely a value is to be an agency name"""
    score = 0
    v_lower = normalize(v)

    # Agency word matching
    for word in AGENCY_WORDS:
        if word in v_lower:
            score += 3

    # Common patterns
    if " of " in v_lower:
        score += 2

    if "," in v:
        score += 1

    # Length check
    if len(v) > 200:
        score -= 5

    # Key hint bonus
    if key_hint:
        key_norm = normalize(key_hint)
        if any(term in key_norm for term in ['department', 'agency', 'division', 'organization']):
            score += 5

    return score


def score_reference(v, key_hint=None):
    """Score how likely a value is to be a reference number"""
    score = 0

    # Pattern match
    if REF_PATTERN.search(str(v)):
        score += 5

    # Format characteristics
    if re.match(r'^[A-Z]{2,4}[-\s]?\d', str(v), re.IGNORECASE):
        score += 3

    # Key hint bonus
    if key_hint and 'ref' in normalize(key_hint):
        score += 5

    # Penalties
    if len(str(v)) > 80:
        score -= 3

    if ' ' in str(v) and len(str(v).split()) > 4:
        score -= 2

    return score


# ==================================================
# Field Detector (Enhanced)
# ==================================================

def detect_fields(data: dict):
    """Enhanced field detection using headers and scoring"""

    # First, detect headers
    headers = detect_headers(data)

    title = None
    agency = None
    ref = None
    location = None
    status = None
    deadline = None
    description = None

    # Use header-based extraction first
    if 'title' in headers:
        title = clean(data.get(headers['title']))
    if 'reference' in headers:
        ref = clean(data.get(headers['reference']))
    if 'agency' in headers:
        agency = clean(data.get(headers['agency']))
    if 'status' in headers:
        status = clean(data.get(headers['status']))
    if 'location' in headers:
        location = clean(data.get(headers['location']))
    if 'deadline' in headers:
        deadline = parse_date_safe(data.get(headers['deadline']))
    if 'description' in headers:
        description = clean(data.get(headers['description']))

    # Score-based detection for missing fields
    best_title = (title or "", -100)
    best_agency = (agency or "", -100)
    best_ref = (ref or "", -100)

    for key, val in data.items():
        v = clean(val)
        if not v:
            continue

        # Title scoring
        if not title or best_title[1] < 3:
            t_score = score_title(v, key)
            if t_score > best_title[1] and is_valid_title(v):
                best_title = (v, t_score)

        # Agency scoring
        if not agency or best_agency[1] < 3:
            a_score = score_agency(v, key)
            if a_score > best_agency[1]:
                best_agency = (v, a_score)

        # Reference scoring
        if not ref or best_ref[1] < 3:
            r_score = score_reference(v, key)
            if r_score > best_ref[1] and is_valid_ref(v):
                best_ref = (v, r_score)

        # Location detection (state codes)
        if not location and str(v).upper() in STATE_CODES:
            location = str(v).upper()

    # Apply best scores if header-based didn't work
    if not title and best_title[1] > 0:
        title = best_title[0]

    if not agency and best_agency[1] > 3:
        agency = best_agency[0]

    if not ref and best_ref[1] > 0:
        ref = best_ref[0]

    # Clean agency
    agency = clean_agency(agency, title)

    # Get deadline if not found via header
    if not deadline:
        deadline = extract_any_date(data)

    return title, agency, ref, location, status, deadline, description


# ==================================================
# Agency Cleanup
# ==================================================

def clean_agency(agency, title):
    """Clean and validate agency name"""
    if not agency:
        return None

    # Prevent title reuse
    if title and normalize(agency) == normalize(title):
        return None

    agency = agency.strip()

    # DB limit
    if len(agency) > 200:
        agency = agency[:200]

    # Reject paragraphs
    if len(agency.split()) > 25:
        return None

    # Reject if it looks like a title
    if score_title(agency) > score_agency(agency):
        return None

    return agency


# ==================================================
# Source
# ==================================================

async def get_default_source(db):
    """Get or create the Excel Import source"""
    q = await db.execute(
        select(Source).where(Source.name == "Excel Import")
    )

    source = q.scalar_one_or_none()

    if not source:
        source = Source(
            name="Excel Import",
            url="internal://excel-import",
            description="Imported from Excel",
            scraper_type="excel",
            status="ACTIVE",
            is_active=True
        )

        db.add(source)
        await db.commit()
        await db.refresh(source)

    return source


# ==================================================
# Status
# ==================================================

def normalize_status(v):
    """Normalize status values"""
    if not v:
        return "open"

    s = normalize(v)

    if any(term in s for term in ['open', 'active', 'available']):
        return "open"

    if any(term in s for term in ['close', 'complete', 'award']):
        return "closed"

    if any(term in s for term in ['expire', 'cancel']):
        return "expired"

    if 'pend' in s:
        return "pending"

    return "open"


# ==================================================
# Keywords
# ==================================================

async def match_keywords(db, tender, text):
    """Match keywords against tender text"""
    if not text:
        return

    res = await db.execute(
        select(Keyword).where(Keyword.is_active == True)
    )

    keywords = res.scalars().all()
    text = normalize(text)

    for kw in keywords:
        key = normalize(kw.keyword)
        pattern = r"\b" + re.escape(key) + r"\b"

        if not re.search(pattern, text):
            continue

        # Check if match already exists
        exists = await db.execute(
            select(TenderKeywordMatch).where(
                and_(
                    TenderKeywordMatch.tender_id == tender.id,
                    TenderKeywordMatch.keyword_id == kw.id
                )
            )
        )

        if exists.scalar():
            continue

        # Create match
        db.add(
            TenderKeywordMatch(
                tender_id=tender.id,
                keyword_id=kw.id,
                match_location="excel"
            )
        )

        kw.match_count += 1
        kw.last_match_date = datetime.utcnow()


# ==================================================
# Importer
# ==================================================

async def import_excel_tenders(db):
    """Import tenders from Excel rows"""

    source = await get_default_source(db)

    res = await db.execute(select(ExcelRowRaw))
    rows = res.scalars().all()

    imported = 0
    skipped = 0
    errors = []

    for row in rows:
        try:
            data = row.row_data or {}

            if not data:
                skipped += 1
                continue

            # -----------------------------
            # Detect fields
            # -----------------------------

            title, agency, ref, location, status, deadline, description = detect_fields(data)

            # -----------------------------
            # Validate minimum requirements
            # -----------------------------

            if not title:
                skipped += 1
                errors.append(f"Row {row.id}: No title detected")
                continue

            # Generate reference if missing
            if not ref:
                ref = f"AUTO-{row.sheet_id}-{row.id}"

            # Final safety on reference length
            if len(ref) > 80:
                ref = f"AUTO-{row.sheet_id}-{row.id}"

            # Normalize status
            status = normalize_status(status)

            # -----------------------------
            # Check for duplicates
            # -----------------------------

            exists = await db.execute(
                select(Tender).where(Tender.reference_id == ref)
            )

            if exists.scalar():
                skipped += 1
                continue

            # -----------------------------
            # Create description
            # -----------------------------

            # Use detected description or combine all values
            if not description:
                desc_parts = [str(v) for v in data.values() if clean(v)]
                description = " | ".join(desc_parts)[:2000]
            else:
                description = description[:2000]

            # -----------------------------
            # Create tender
            # -----------------------------

            tender = Tender(
                title=title[:500],
                reference_id=ref[:255],
                description=description,
                agency_name=agency[:200] if agency else None,
                agency_location=location,
                deadline_date=deadline,
                status=status,
                source_id=source.id,
                imported_from_excel=True,
                excel_row_id=row.id
            )

            db.add(tender)
            await db.flush()

            # -----------------------------
            # Match keywords
            # -----------------------------

            full_text = f"{title} {description}"
            await match_keywords(db, tender, full_text)

            imported += 1

        except Exception as e:
            errors.append(f"Row {row.id}: {str(e)}")
            skipped += 1
            continue

    # Update source stats
    source.total_tenders += imported
    source.last_fetch_at = datetime.utcnow()
    source.last_success_at = datetime.utcnow()

    await db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "total": len(rows),
        "errors": errors[:50]  # Limit error list
    }