import { SignJWT } from "jose";
import { NextResponse } from "next/server";

const SECRET = new TextEncoder().encode(
  process.env.AUTH_SECRET ?? "change-me-shared-with-nextauth",
);

// Issues a short-lived demo JWT for hackathon demos (no real NextAuth needed).
export async function POST() {
  const token = await new SignJWT({
    sub: "demo-user-001",
    email: "demo@helplk.ai",
  })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("8h")
    .sign(SECRET);

  return NextResponse.json({ token });
}
