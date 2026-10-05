import { API_KEY } from "$env/static/private";

export async function load({ fetch, params }) {
  const response = await fetch(
    `https://api.example.com/users/${params.id}?key=${API_KEY}`,
  );
  return { bio: (await response.json()).bio };
}
