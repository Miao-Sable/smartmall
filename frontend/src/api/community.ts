import request from './request'

export interface Review {
  id: number
  content: string
  product_name: string
  tag: string
  barcode: string
  author_nickname: string
  created_at: string
}

export interface ReviewCreate {
  content: string
  product_name?: string
  tag?: string
  barcode?: string
}

export const getReviewsApi = () => request.get<Review[]>('/community/reviews').then((r) => r.data)

export const getProductReviewsApi = (barcode: string) =>
  request.get<Review[]>('/community/reviews', { params: { barcode } }).then((r) => r.data)

export const createReviewApi = (data: ReviewCreate) =>
  request.post<Review>('/community/reviews', data).then((r) => r.data)
