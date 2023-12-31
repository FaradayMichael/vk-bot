from enum import StrEnum


class DBTables(StrEnum):
    USERS = 'users'
    BRANDS = 'brands'
    COLLECTIONS = 'collections'
    WATCHES = 'watches'
    WATCH_FUNCTIONS = 'watch_functions'
    WATCH_FUNCTIONS_WATCH = 'watch_functions_watch'
    WATCH_PHOTOS = 'watch_photos'
    PRICES_CHART = 'prices_chart'
    WALLET = 'wallet'
    CONTACT = 'contacts'
    DELIVERY_COSTS = 'delivery_costs'
    INVESTMENTS = 'investments'
    COUNTRIES = 'countries'
    CITIES = 'cities'
    PURCHASES = 'purchases'
    PAYMENT_HISTORY = 'payment_history'
    STORAGE_FILES = 'storage_files'
    WATCH_BODY_MATERIALS = 'watch_body_materials'
    WATCH_STRAP_MATERIALS = 'watch_strap_materials'
    WATCH_DIAL_COLORS = 'watch_dial_colors'
    JEWELRY = 'jewelry'
    JEWELRY_TYPES = "jewelry_types"
    JEWELRY_COLORS = "jewelry_colors"
    JEWELRY_MATERIALS = "jewelry_materials"
    JEWELRY_PHOTOS = "jewelry_photos"
    ACCESSORIES = "accessories"
    ACCESSORIES_TYPES = "accessories_types"
    ACCESSORIES_PHOTOS = "acc_photos"
    CARTS = "carts"
    ORDERS = "orders"
    TRANSACTIONS = "transactions"
    TRANSLATED_PROPERTIES = "translated_properties"
    DELIVERY_ADDRESSES = "delivery_addresses"
    FAVORITES = "favorites"
    USER_WATCHES = "user_watches"
    USER_WATCH_PHOTOS = "user_watch_photos"
    USER_COLLECTIONS = "user_collections"
    USER_WATCH_COLLECTION = "user_watch_collection"
    MISC_CONFIGS = "misc_configs"
    LOCATIONS = 'locations'
    COLLECTIONS_WATCHES_LINKAGE = 'collections_watches'
    PRICE_HISTORY = "price_history"
    COMPANY_CURRENT_AMOUNTS = 'company_current_amounts'
    COMPANY_USED = 'company_used'
