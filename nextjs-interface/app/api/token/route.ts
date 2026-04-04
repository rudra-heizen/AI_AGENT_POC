import { AccessToken, VideoGrant } from "livekit-server-sdk";
import { NextResponse } from "next/server";

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export const revalidate = 0;

/**
 * Token endpoint compatible with LiveKit's TokenSource.endpoint() API.
 * Expects POST with snake_case fields, returns { server_url, participant_token }.
 */
export async function POST(req: Request) {
  try {
    if (!LIVEKIT_URL || !API_KEY || !API_SECRET) {
      return NextResponse.json(
        { message: "Server misconfigured" },
        { status: 500 }
      );
    }

    const body = await req.json();

    const suffix = crypto.randomUUID().substring(0, 8);
    const roomName =
      body.room_name ?? body.roomName ?? `interview-room-${suffix}`;
    const participantIdentity =
      body.participant_identity ?? body.participantName ?? `user-${suffix}`;
    const participantName = body.participant_name ?? participantIdentity;

    const at = new AccessToken(API_KEY, API_SECRET, {
      identity: participantIdentity,
      name: participantName,
      ttl: "15m",
    });

    const grant: VideoGrant = {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
      canUpdateOwnMetadata: true,
    };
    at.addGrant(grant);

    if (body.participant_metadata) {
      at.metadata = body.participant_metadata;
    }
    if (body.participant_attributes) {
      at.attributes = body.participant_attributes;
    }
    if (body.room_config) {
      // Import RoomConfiguration if needed for agent dispatch via token
      // at.roomConfig = RoomConfiguration.fromJson(body.room_config);
    }

    const token = await at.toJwt();

    // Return in the format TokenSource.endpoint() expects
    return NextResponse.json(
      {
        server_url: LIVEKIT_URL,
        participant_token: token,
      },
      {
        headers: { "Cache-Control": "no-store" },
      }
    );
  } catch (error) {
    console.error("Error generating token:", error);
    return NextResponse.json(
      { message: "Token generation failed" },
      { status: 500 }
    );
  }
}
