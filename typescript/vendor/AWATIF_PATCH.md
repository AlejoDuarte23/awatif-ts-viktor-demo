# Awatif oriented-shell correction

The Awatif v2 source used for this demo originally derived triangular-shell
shape functions from each node's global `x` and `y` values. That works for a
horizontal plate but degenerates vertical shells such as a tube or stiffener.

The local bundle projects every three-node shell to its element-local `x/y`
plane before building shell stiffness and reporting membrane/bending results.
It also maps the complete 9-by-9 membrane stiffness matrix to the shell's
18-by-18 degrees of freedom. The element transformation and solver remain
otherwise unchanged.

This is a demo-specific integration patch, not an upstream Awatif release.
