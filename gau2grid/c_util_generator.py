"""
Builds c utility routines
"""

from . import utility

### Pybind11 binders


def pybind11_func(cg, name, grad, call_name, max_L):
    """
    A function that builds the PyBind11 wrappers for the different pybind11 funcs.
    """

    # Figure out what we need to add per deriv
    deriv_indices = utility.get_deriv_indices(grad)

    # Write out wrapper functions
    sig = """void %s(int L, py::array_t<double> arr_xyz, py::array_t<double> arr_coeffs,
py::array_t<double> arr_exponents, py::array_t<double> arr_center, bool spherical,
py::array_t<double> arr_out""" % name

    # Pad out deriv outputs
    for cart in deriv_indices:
        sig += ", py::array_t<double> arr_%s_out" % cart

    sig += ")"
    cg.start_c_block(sig)
    cg.blankline()

    # Grab the pointers
    cg.write('// Grab array pointers')
    cg.write('auto xyz = arr_xyz.unchecked<2>()')
    cg.write('auto coeffs = arr_coeffs.unchecked<1>()')
    cg.write('auto exponents = arr_exponents.unchecked<1>()')
    cg.write('auto center = arr_center.unchecked<1>()')
    cg.write('auto out = arr_out.mutable_unchecked<2>()')

    # Pad out deriv pointers
    for cart in deriv_indices:
        cg.write("auto out_%s = arr_%s_out.mutable_unchecked<2>()" % (cart, cart))

    cg.blankline()

    # Run through checks
    cg.write('// XYZ is of size 3')
    cg.start_c_block('if (L > %d)' % max_L)
    cg.write(
        '    throw std::invalid_argument("Exceeded compiled angular momentum of %d. Please recompile with a higher angular momentum.\\n")'
        % max_L)
    cg.close_c_block()

    cg.write('// XYZ is of size 3')
    cg.start_c_block('if (arr_xyz.shape(0) != 3)')
    cg.write('    throw std::length_error("Length of XYZ array must be (3, n).\\n")')
    cg.close_c_block()
    cg.blankline()

    cg.write('// Coeff matches exponent shape')
    cg.start_c_block('if (coeffs.shape(0) != exponents.shape(0))')
    cg.write('    throw std::length_error("Length of coefficients and exponents must match.\\n")')
    cg.close_c_block()
    cg.blankline()

    cg.write('// Center is of size 3')
    cg.start_c_block('if (center.shape(0) != 3)')
    cg.write('    throw std::length_error("Length of center vector must be 3 (X, Y, Z).\\n")')
    cg.close_c_block()
    cg.blankline()

    cg.write('// Make sure output length matches')
    cg.write('size_t nsize')
    cg.start_c_block('if (spherical)')
    cg.write('    nsize = 2 * L + 1')
    cg.write('} else {', endl="")
    cg.write('    nsize = ((L + 2) * (L + 1)) / 2')
    cg.close_c_block()
    cg.blankline()

    cg.start_c_block('if (out.shape(0) != nsize)')
    cg.write('    throw std::length_error("Size of the output array does not match the angular momentum.\\n")')
    cg.close_c_block()

    for cart in deriv_indices:
        cg.start_c_block('if (out_%s.shape(0) != nsize)' % cart)
        cg.write('    throw std::length_error("Size of the output %s array does not match the angular momentum.\\n")' %
                 cart.upper())
        cg.close_c_block()
    cg.blankline()

    cg.write('// Ensure lengths match')
    cg.start_c_block('if (out.shape(1) != arr_xyz.shape(1))')
    cg.write('    throw std::length_error("Size of the output array and XYZ array must be the same.\\n")')
    cg.close_c_block()

    # Pad out deriv length checkers
    for cart in deriv_indices:
        cg.start_c_block('if (out_%s.shape(1) != arr_xyz.shape(1))' % cart)
        cg.write('    throw std::length_error("Size of the output %s array and XYZ array must be the same.\\n")' %
                 cart.upper())
        cg.close_c_block()
    cg.blankline()

    cg.write("// Call the GG helper function")
    call_func = call_name + "(L, xyz.shape(1)"
    call_func += ", xyz.data(0, 0), xyz.data(1, 0), xyz.data(2, 0)"
    call_func += ", coeffs.shape(0), coeffs.data(0), exponents.data(0)"
    call_func += ", center.data(0)"
    call_func += ", spherical"
    call_func += ", out.mutable_data(0, 0)"
    for cart in deriv_indices:
        call_func += ", out_%s.mutable_data(0, 0)" % cart
    call_func += ")"

    cg.write(call_func)

    cg.close_c_block()


def pybind11_transpose(cg, func_name, wrapper_name):
    """
    Wraps the transpose functions in pybind11
    """

    sig = "void %s(py::array_t<double> arr_input" % wrapper_name
    sig += ", py::array_t<double> arr_output)"

    cg.start_c_block(sig)
    cg.write("auto input = arr_input.unchecked<2>()")
    cg.write("auto output = arr_output.mutable_unchecked<2>()")
    cg.write("size_t n = input.shape(0)")
    cg.write("size_t m = input.shape(1)")
    cg.blankline()

    cg.write('// Check shapes')
    cg.start_c_block('if (input.shape(0) != output.shape(1))')
    cg.write('    throw std::length_error("Input tranpose shape 0 does not match output transpose shape 1.\\n")')
    cg.close_c_block()
    cg.blankline()

    cg.start_c_block('if (input.shape(1) != output.shape(0))')
    cg.write('    throw std::length_error("Input tranpose shape 1 does not match output transpose shape 0.\\n")')
    cg.close_c_block()
    cg.blankline()

    cg.write("%s(n, m, input.data(0, 0), output.mutable_data(0, 0))" % func_name)

    cg.close_c_block()


### Tranposers


def naive_transpose(cg):
    """
    A completely naive tranpose to swap data
    """

    sig = "void gg_naive_transpose(size_t n, size_t m, const double* __restrict__ input, double* __restrict__ output)"
    cg.start_c_block(sig)

    cg.start_c_block("for (size_t i = 0; i < n; i++)")

    # Inner block
    cg.start_c_block("for (size_t j = 0; j < m; j++)")
    cg.write("output[j * n + i] = input[i * m + j]")
    cg.close_c_block()

    # Outer block
    cg.close_c_block()

    cg.close_c_block()
    return sig


def fast_transpose(cg, inner_block):
    """
    Builds a fast transpose using an internal blocking scheme in an attempt to vectorize IO from/to DRAM
    """

    sig = "void gg_fast_transpose(size_t n, size_t m, const double* __restrict__ input, double* __restrict__ output)"
    cg.start_c_block(sig)
    cg.blankline()

    cg.write("// Temps")
    cg.write("double tmp[%d]  __attribute__((aligned(64)))" % (inner_block * inner_block))

    cg.write("// Sizing")
    cg.write("size_t nblocks = n / %d" % inner_block)
    cg.write("nblocks += (n %% %d) ? 1 : 0" % inner_block)

    cg.write("size_t mblocks = m / %d" % inner_block)
    cg.write("mblocks += (m %% %d) ? 1 : 0" % inner_block)
    # cg.write('printf("Blocks: %ld %ld\\n", nblocks, mblocks)')

    cg.write("// Outer blocks")
    cg.start_c_block("for (size_t nb = 0; nb < nblocks; nb++)")
    cg.write("const size_t nstart = nb * %d" % inner_block)
    cg.write("size_t nremain = ((nstart + %d) > n) ? (n - nstart) : %d" % (inner_block, inner_block))

    cg.start_c_block("for (size_t mb = 0; mb < mblocks; mb++)")
    cg.write("const size_t mstart = mb * %d" % inner_block)
    cg.write("size_t mremain = ((mstart + %d) > m) ? (m - mstart) : %d" % (inner_block, inner_block))

    # cg.start_c_block("if ((nremain == 0) & (mremain > 0))")
    # cg.write("nremain++;")
    # cg.close_c_block()

    # cg.start_c_block("if ((mremain == 0) & (nremain > 0))")
    # cg.write("mremain++;")
    # cg.close_c_block()
    # cg.write('printf("(n,m)%ld %ld | %ld %ld\\n", nb, mb, nremain, mremain)')

    # Pull block
    cg.write("// Copy data to inner block")
    # cg.write('printf("%ld %ld | %ld\\n ", mstart, nstart, start)')
    cg.start_c_block("for (size_t l = 0; l < nremain; l++)")
    cg.write("const size_t start = (nstart + l) * m + mstart")
    # cg.write("PRAGMA_VECTORIZE", endl="")
    cg.start_c_block("for (size_t k = 0; k < mremain; k++)")

    # cg.write("tmp[l * %d + k] = input[start + k]" % inner_block)
    cg.write("tmp[k * %d + l] = input[start + k]" % inner_block)

    # cg.write('printf("(%ld %ld %lf) ", l * 2+ k, start +k, input[start + k])')
    # cg.write('printf("%%lf ", tmp[k * %d + l])' % inner_block)
    cg.close_c_block()
    cg.close_c_block()
    # cg.write('printf("\\n--\\n")')
    # cg.start_c_block("for (size_t k = 0; k < 4; k++)")
    # cg.write('printf("%lf ", tmp[k])')
    # cg.close_c_block()
    # cg.write('printf("\\n--\\n")')

    # Tranpose block
    # cg.write("// Transpose inner block")
    # cg.start_c_block("for (size_t k = 0; k < %d; k++)" % inner_block)
    # cg.start_c_block("for (size_t l = k; l < %d; l++)" % inner_block)
    # # cg.write('printf("%ld %ld \\n", k, l)')
    # cg.write("const double itmp = tmp[l * %d + k]" % inner_block)
    # cg.write("tmp[l * %d + k] = tmp[k * %d + l]" % (inner_block, inner_block))
    # cg.write("tmp[k * %d + l] = itmp" % (inner_block))
    # cg.close_c_block()
    # cg.close_c_block()
    # cg.write('printf("--\\n")')
    # cg.start_c_block("for (size_t k = 0; k < 4; k++)")
    # cg.write('printf("%lf ", tmp[k])')
    # cg.close_c_block()
    # cg.write('printf("\\n--\\n")')

    # Push block
    cg.write("// Copy data to inner block")
    cg.start_c_block("for (size_t k = 0; k < mremain; k++)")
    cg.write("const size_t start = (mstart + k) * n + nstart")
    # cg.write("PRAGMA_VECTORIZE", endl="")
    cg.start_c_block("for (size_t l = 0; l < nremain; l++)")
    # cg.write('printf("(k,l) %ld %ld | %ld\\n", k, l, start+l)')

    cg.write("output[start + l] = tmp[k * %d + l]" % inner_block)
    cg.close_c_block()
    cg.close_c_block()
    # cg.write('printf("--------\\n")')

    # cg.start_c_block("for (size_t k = 0; k < %d; k++)" % inner_block)
    # cg.start_c_block("for (size_t l = 0; l < %d; l++)" % inner_block)
    # cg.write("tmp[k * %d + l] = 0.0" % inner_block)
    # cg.close_c_block()
    # cg.close_c_block()

    # Outer block
    cg.close_c_block()
    cg.close_c_block()

    cg.close_c_block()

    return sig


### Data copiers


def block_copy(cg):
    """
    Copies a small block of data back to a larger array.
    """

    sig = "void block_copy(size_t n, size_t m, const double* __restrict__ input, size_t is, double* __restrict__ output, size_t os, const int trans)"
                            # nout, nremain

    cg.start_c_block(sig)
    cg.blankline()
    cg.start_c_block("for (size_t i = 0; i < n; i++)")
    cg.write("const size_t out_shift = i * os")
    cg.write("const size_t inp_shift = i * is")

    # Inner copy over block
    cg.blankline()
    # cg.write("PRAGMA_VECTORIZE", endl="")
    cg.start_c_block("for (size_t j = 0; j < m; j++)")
    # cg.write("output[is * j + i] = input[i * is + j]")
    cg.write("output[out_shift + j] = input[inp_shift + j]")
    cg.close_c_block()

    # Close i loop
    cg.close_c_block()

    # Close func
    cg.close_c_block()
    return sig