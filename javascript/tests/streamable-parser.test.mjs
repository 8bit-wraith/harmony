import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { after, before, test } from "node:test";
import {
  initSync,
  JsStreamableParser,
  load_harmony_encoding,
} from "../dist/web/openai_harmony.js";

let encoding;

before(async () => {
  initSync({
    module: await readFile(new URL("../dist/web/openai_harmony_bg.wasm", import.meta.url)),
  });
  const vocab = await readFile(
    process.env.HARMONY_TEST_VOCAB ??
      new URL("../../demo/harmony-demo/public/o200k_base.tiktoken", import.meta.url),
  );
  const server = createServer((request, response) => {
    if (request.url !== "/o200k_base.tiktoken") {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200).end(vocab);
  });
  try {
    await new Promise((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", resolve);
    });
    encoding = await load_harmony_encoding(
      "HarmonyGptOss",
      `http://127.0.0.1:${server.address().port}/`,
    );
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

after(() => encoding?.free());

function parse(text, role) {
  const parser = new JsStreamableParser(encoding, role);
  try {
    for (const token of encoding.encode(text, encoding.specialTokens())) {
      parser.process(token);
    }
    return JSON.parse(parser.messages);
  } finally {
    parser.free();
  }
}

test("full conversations preserve the first developer role", () => {
  assert.deepEqual(
    parse("<|start|>developer<|message|>Synthetic browser check.<|end|><|start|>assistant<|message|>Ready.<|return|>"),
    [
      { role: "developer", content: "Synthetic browser check." },
      { role: "assistant", content: "Ready." },
    ],
  );
});

test("full user messages do not acquire a bogus recipient", () => {
  assert.deepEqual(parse("<|start|>user<|message|>Hello.<|end|>"), [
    { role: "user", content: "Hello." },
  ]);
});

test("first-message tool routing and channel are preserved", () => {
  assert.deepEqual(
    parse('<|start|>assistant to=functions.lookup<|channel|>commentary<|message|>{"query":"synthetic"}<|call|>'),
    [{ role: "assistant", content: '{"query":"synthetic"}', channel: "commentary", recipient: "functions.lookup" }],
  );
});

test("explicit roles still support completion prefixes", () => {
  assert.deepEqual(parse("<|message|>Ready.<|return|>", "assistant"), [
    { role: "assistant", content: "Ready." },
  ]);
});

test("invalid explicit roles still fail", () => {
  assert.throws(() => new JsStreamableParser(encoding, "invalid-role"));
});
