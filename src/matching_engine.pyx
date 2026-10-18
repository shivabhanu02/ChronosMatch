
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

cpdef int compare_prices(double incoming_price, double resting_price,
                         bint is_buy):
    """Return 1 if the incoming order crosses the resting price."""
    if is_buy:
        return 1 if incoming_price >= resting_price else 0
    return 1 if incoming_price <= resting_price else 0
