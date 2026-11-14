import api from "@/services/api"
import type { Tag } from "@/types"

export async function listTags(): Promise<Tag[]> {
  const { data } = await api.get<Tag[]>("/tags")
  return data
}

/** Create a tag. The backend answers 409 if the name already exists. */
export async function createTag(name: string): Promise<Tag> {
  const { data } = await api.post<Tag>("/tags", { name })
  return data
}
