
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

cpdef int compare_prices(
    double incoming_price,
    double resting_price,
    bint is_buy
):
    """Check whether an incoming order crosses the resting price."""
    if is_buy:
        return 1 if incoming_price >= resting_price else 0
    return 1 if incoming_price <= resting_price else 0


cpdef tuple match_fifo_quantities(
    long long incoming_quantity,
    long long[::1] resting_quantities
):
    """
    Match an incoming quantity against resting orders in FIFO order.

    Updates resting_quantities in place.
    Returns (fill_quantities, remaining_incoming_quantity).
    """
    cdef Py_ssize_t i
    cdef long long available
    cdef long long fill
    cdef list fills = []

    if incoming_quantity <= 0:
        raise ValueError("Incoming quantity must be positive")

    for i in range(resting_quantities.shape[0]):
        if resting_quantities[i] <= 0:
            raise ValueError("Resting quantities must be positive")

    for i in range(resting_quantities.shape[0]):
        available = resting_quantities[i]

        if incoming_quantity <= 0:
            fills.append(0)
            continue

        if incoming_quantity < available:
            fill = incoming_quantity
        else:
            fill = available

        resting_quantities[i] = available - fill
        incoming_quantity -= fill
        fills.append(fill)

    return fills, incoming_quantity
