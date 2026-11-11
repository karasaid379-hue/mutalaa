import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { problem, useFakeApi } from './fake-api';
import { renderApp } from './render-app';

describe('login form', () => {
  const fake = useFakeApi();

  it('ties the failure message to both fields after a wrong password', async () => {
    fake.get('/api/v1/auth/me', problem(401, 'oturum-acilamadi'));
    fake.post('/api/v1/auth/login', problem(401, 'oturum-acilamadi'));
    const { user } = renderApp(fake, '/giris');
    const email = await screen.findByLabelText(tr.session.email);
    const password = screen.getByLabelText(tr.session.password);
    expect(email).not.toHaveAttribute('aria-invalid');

    await user.type(email, 'baska@deneme.test');
    await user.type(password, 'yanlis');
    await user.click(screen.getByRole('button', { name: tr.session.submit }));

    const message = (
      await screen.findByText(tr.problem.contexts.login['oturum-acilamadi'])
    ).closest('[role="alert"]')!;
    await waitFor(() => expect(email).toHaveAttribute('aria-invalid', 'true'));
    expect(password).toHaveAttribute('aria-invalid', 'true');
    for (const field of [email, password]) {
      const target = document.getElementById(field.getAttribute('aria-describedby')!)!;
      expect(target).toContainElement(message as HTMLElement);
    }
  });
});
