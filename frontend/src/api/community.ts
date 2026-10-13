import request from './request'

export interface Review {
  id: number
  content: string
  product_name: string
  tag: string
  author_nickname: string
  created_at: string
}

export interface ReviewCreate {
  content: string
  product_name?: string
  tag?: string
}

export const getReviewsApi = () => request.get<Review[]>('/community/reviews').then((r) => r.data)

export const createReviewApi = (data: ReviewCreate) =>
  request.post<Review>('/community/reviews', data).then((r) => r.data)
