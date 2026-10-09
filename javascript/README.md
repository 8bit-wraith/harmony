# @openai/harmony

This version is still in active development and not currently published.

If you want to use it for demo purposes you can run:

```bash
make javascript
```

After building `dist/web` and provisioning the demo's vocabulary, run the
JavaScript binding regressions with `npm run test:wasm` from this directory.
The tests serve that vocabulary on a temporary loopback port and do not download
it. Set `HARMONY_TEST_VOCAB` to use an existing vocabulary file elsewhere.

Omit the `JsStreamableParser` role when the input includes the full start token
and role header. Pass a role only when parsing a completion whose role prefix
has already been consumed.
