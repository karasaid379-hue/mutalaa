import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useApi } from '@/app/api-context';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { tr } from '@/i18n/tr';
import { safeNext } from '@/lib/safe-next';
import { ME_PATH } from '@/review/queries';

/** `/giris`: e-mail and password. After a logout (`?cikis=1`) it says so and explains the development auto login. */
export function Component() {
  const api = useApi();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const loggedOut = params.get('cikis') === '1';
  const next = safeNext(params.get('sonraki'));
  const login = api.$api.useMutation('post', '/api/v1/auth/login');
  const ids = { email: useId(), password: useId() };
  const [email, setEmail] = useState('');
  const [parola, setParola] = useState('');
  const errorRef = useRef<HTMLDivElement>(null);
  const failed = login.isError;

  useEffect(() => {
    if (failed) errorRef.current?.focus();
  }, [failed]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const session = await login.mutateAsync({ body: { email, parola } });
      queryClient.setQueryData(api.$api.queryOptions('get', ME_PATH).queryKey, session);
      await navigate(next, { replace: true });
    } catch {
      // The error is shown from the mutation state below.
    }
  }

  return (
    <main className="mx-auto flex max-w-md flex-col gap-4 p-6">
      <PageHeading>{tr.session.loginTitle}</PageHeading>
      <p className="text-sm text-muted-foreground">{tr.session.loginIntro}</p>
      {loggedOut ? (
        <div
          className="flex flex-col gap-2 rounded-lg border p-3 text-sm"
          data-testid="logged-out-note"
        >
          <p className="font-medium">{tr.session.loggedOut}</p>
          <p>{tr.session.devAutoLoginNote}</p>
          <Link to="/" className="underline">
            {tr.session.backToPanel}
          </Link>
        </div>
      ) : null}
      {failed ? <ProblemMessage ref={errorRef} error={login.error} context="login" /> : null}
      <form className="flex flex-col gap-3" noValidate onSubmit={(event) => void submit(event)}>
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.email}>{tr.session.email}</Label>
          <Input
            id={ids.email}
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.password}>{tr.session.password}</Label>
          <Input
            id={ids.password}
            type="password"
            autoComplete="current-password"
            value={parola}
            onChange={(event) => setParola(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={login.isPending}>
          {login.isPending ? tr.session.submitting : tr.session.submit}
        </Button>
      </form>
    </main>
  );
}
