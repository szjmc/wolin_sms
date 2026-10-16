// 页面共用的业务响应类型；所有接口字段使用 snake_case。
export interface Student {
  id: number; student_no: string; name: string; class_id: number; class_no: string;
  class_name?: string | null; gender: string; birth_date: string; age: number;
  hometown: string | null; graduate_school: string | null; major: string | null;
  education: string | null; consultant_no: string | null; avatar_url: string | null;
  training_enrollment_date: string | null; training_graduation_date: string | null; employment_status: string;
  created_at?: string; updated_at?: string;
}
export interface Teacher {
  id: number; teacher_no: string; name: string; gender: string | null;
  specialty: string | null; phone: string | null; contact_info: string | null;
  teaching_years: string; teacher_status: string; teaching_status: string;
}
export interface ClassItem {
  id: number; class_no: string; class_name: string; start_date: string;
  completion_date: string | null; class_status: string; total_students?: number;
  head_teacher: Teacher | null; teachers: Teacher[];
}
export interface Relation {
  id: number; class_id: number; class_no: string; class_name: string; class_status: string;
  teacher_id: number; teacher_no: string; teacher_name: string; specialty: string | null;
  phone: string | null; teacher_status: string; teaching_status: string;
  relation_type: string; created_at: string;
}
export interface Score {
  id: number; student_id: number; student_no: string; name: string; class_id: number;
  class_no: string; class_name: string; exam_no: number; score: string;
  grade: string; created_at: string; updated_at: string;
}
export interface ScoreSummary {
  total: number; average_score: string | null; pass_count: number; excellent_count: number;
}
export interface Employment {
  id: number; student_id: number; student_no?: string; student_name_snapshot: string;
  class_id?: number | null; class_no_snapshot: string;
  company_name: string; employment_city: string | null; position: string | null;
  salary_amount: string; salary_period: string; annualized_salary: string; offer_status: string;
  employment_open_date: string | null; offer_date: string | null;
  past_salary_amount: string | null; past_salary_period: string | null;
  previous_position: string | null; past_graduation_date: string | null;
  graduation_years: number | null; created_at?: string; updated_at?: string;
}
export interface SalaryComparison {
  employment_record_id: number; student_id: number; student_name_snapshot: string;
  previous_position: string | null; position: string | null;
  past_salary_amount: string | null; past_salary_period: string | null;
  salary_amount: string; salary_period: string;
  past_annualized_salary: string | null; annualized_salary: string;
  monthly_before: string | null; monthly_after: string;
  annual_increase: string | null; increase_percent: string | null;
  comparison_available: boolean;
}
export interface ClassOverview {
  class_info: ClassItem; total_students: number; male_count: number; female_count: number;
  other_count: number; graded_students: number; total_scores: number; passing_scores: number;
  pass_rate: string | null; average_score: string | null; qualified_students: number;
  employed_students: number;
}
export interface PastExperience {
  id: number; student_id: number; past_salary_amount: string | null; past_salary_period: string | null;
  work_years: string; graduation_date: string | null; intended_city: string | null; previous_position: string | null;
}
