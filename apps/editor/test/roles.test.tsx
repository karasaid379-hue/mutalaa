// Role hiding (A15.3): the panel hides what the user cannot use; the server still decides. The releases screen
// and the unit correction button have their cases in releases-screen.test.tsx and units-screen.test.tsx; this
// file covers the decision form, which the other queues share.
import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { tr } from '@/i18n/tr';
import { DecisionForm } from '@/review/decision-form';
import { ok, useFakeApi } from './fake-api';
import { reviewDetail, session, unitDetail } from './fixtures';
import { renderWithProviders } from './render-app';

describe('decision form: roles', () => {
  const fake = useFakeApi();

  function setup(roles: string[]) {
    fake.get('/api/v1/auth/me', ok(session(roles)));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    return renderWithProviders(fake, <DecisionForm review={reviewDetail()} onDecided={vi.fn()} />);
  }

  it.each([[[]], [['okuyucu']]])('shows only the role notice for roles %j', async (roles) => {
    setup(roles);
    expect(await screen.findByText(tr.review.noRole)).toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: tr.review.submit })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(tr.review.reason)).not.toBeInTheDocument();
    expect(fake.callsTo('post', '/api/v1/reviews/{id}/decision')).toHaveLength(0);
  });

  it.each([[['editor']], [['admin']], [['admin', 'editor']]])(
    'shows the form for roles %j',
    async (roles) => {
      setup(roles);
      expect(await screen.findByRole('radio', { name: tr.review.approve })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: tr.review.submit })).toBeInTheDocument();
      await waitFor(() => expect(screen.queryByText(tr.review.noRole)).not.toBeInTheDocument());
    },
  );
});
