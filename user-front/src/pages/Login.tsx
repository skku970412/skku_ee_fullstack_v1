import { ChevronRight, LogIn, ShieldCheck } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import ErrorBar from "../components/ui/ErrorBar";
import LabeledInput from "../components/forms/LabeledInput";

interface LoginPageProps {
  email: string;
  password: string;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  canSubmit: boolean;
  loading: boolean;
  error: string | null;
  onSubmit: () => void;
}

export default function LoginPage({
  email,
  password,
  onEmailChange,
  onPasswordChange,
  canSubmit,
  loading,
  error,
  onSubmit,
}: LoginPageProps) {
  return (
    <Card>
      <CardHeader
        icon={<LogIn className="w-5 h-5" />}
        title="로그인"
        subtitle="이메일과 비밀번호를 입력해 주세요."
      />
      <div className="grid gap-3 p-6">
        <LabeledInput
          label="이메일"
          placeholder="you@example.com"
          value={email}
          onChange={onEmailChange}
          type="email"
        />
        <LabeledInput
          label="비밀번호"
          placeholder="••••••"
          value={password}
          onChange={onPasswordChange}
          type="password"
        />
        {error && <ErrorBar msg={error} />}
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500 flex items-center gap-1">
            <ShieldCheck className="w-4 h-4" />
            안전한 인증을 제공합니다.
          </div>
          <Button disabled={!canSubmit || loading} onClick={onSubmit}>
            {loading ? "로그인 중..." : "다음"}
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
