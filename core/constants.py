from datetime import time

from decouple import config

DISPENSARY_STATUS_OPEN = 'Open today'
DISPENSARY_STATUS_CLOSED = 'Closed today'
DISPENSARY_STATUS_PENDING = 'Schedule pending'

DISPENSARY_DETAIL_OPEN = 'Walk-ins and booked appointments can proceed during operating hours.'
DISPENSARY_DETAIL_CLOSED = 'The dispensary is unavailable today. Check back after the next schedule update.'
DISPENSARY_DETAIL_PENDING = 'The dispensary calendar will be configured in the next step.'
DISPENSARY_DETAIL_DEFAULT = 'Default hours apply: 9:00 AM to 5:00 PM.'

DISPENSARY_BADGE_OPEN = 'dispensary-badge--open'
DISPENSARY_BADGE_CLOSED = 'dispensary-badge--closed'
DISPENSARY_BADGE_PENDING = 'dispensary-badge--pending'

DEFAULT_DISPENSARY_OPEN_TIME = time(hour=9, minute=0)
DEFAULT_DISPENSARY_CLOSE_TIME = time(hour=17, minute=0)

MONTHLY_MEDICINE_QUOTA = config('MONTHLY_MEDICINE_QUOTA', default=5, cast=int)
SLOT_GRACE_MINUTES = config('SLOT_GRACE_MINUTES', default=15, cast=int)
AVG_CONSULT_MINUTES = config('AVG_CONSULT_MINUTES', default=7, cast=int)
QUEUE_POLL_INTERVAL_MS = 15000
LOW_STOCK_THRESHOLD = config('LOW_STOCK_THRESHOLD', default=5, cast=int)
