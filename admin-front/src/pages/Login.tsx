import { KeyRound, Lock, LogIn } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import ErrorBar from "../components/ui/ErrorBar";
import LabeledInput from "../components/forms/LabeledInput";

interface LoginPageProps {
  email: string;
  password: string;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  error: string | null;
}

export default function LoginPage({
  email,
  password,
  onEmailChange,
  onPasswordChange,
  onSubmit,
  loading,
  error,
}: LoginPageProps) {
  const canSubmit = email.trim().length > 0 && password.trim().length > 0;

  return (
    <Card>
      <CardHeader
        icon={<LogIn className="w-5 h-5" />}
        title="관리자 로그인"
        subtitle="발급된 관리자 계정으로 로그인해 주세요."
      />
      <div className="grid gap-4 p-6">
        <LabeledInput
          label="관리자 이메일"
          placeholder="admin@example.com"
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
        <Button onClick={onSubmit} disabled={!canSubmit || loading} className="justify-center">
          {loading ? "로그인 중..." : "대시보드로 이동"}
          <Lock className="w-4 h-4 ml-2" />
        </Button>
        <p className="text-xs text-gray-500 flex items-center gap-1">
          <KeyRound className="w-4 h-4" />
          발급된 계정이 없다면 시스템 관리자에게 문의해 주세요.
        </p>
      </div>
    </Card>
  );
}
