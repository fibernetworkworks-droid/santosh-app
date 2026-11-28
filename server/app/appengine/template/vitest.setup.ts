// Hoola App Engine - locked by Hoola. Runs before every test file: each test starts on an empty page.
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());
