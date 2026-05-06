/**
 * Runtime shim for tldraw's rich text editor imports.
 *
 * tldraw's published ESM may import `Editor` from `@tiptap/react`, but in Tiptap v3
 * the `Editor` class lives in `@tiptap/core` and is not a runtime export of `@tiptap/react`.
 * This shim preserves existing exports and adds a runtime `Editor` export.
 */

export * from "@tiptap/react-original";

export { Editor } from "@tiptap/core";

