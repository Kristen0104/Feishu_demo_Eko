/**
 * Runtime shim for `radix-ui` re-exports used by tldraw.
 *
 * In some bundler modes, named exports from the radix-ui meta package can be lost.
 * We re-export everything from the package's ESM entry to ensure stable named exports.
 */

export * from "radix-ui-original";

