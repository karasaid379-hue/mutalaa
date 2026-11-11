// Shared presentation components (A15.3): ProblemMessage, ArabicText, OpenQuestionButton, MissingSection, badges, TextDiff.
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ArabicText } from '@/components/arabic-text';
import { MissingSection } from '@/components/missing-section';
import { OpenQuestionButton } from '@/components/open-question-button';
import { ProblemMessage } from '@/components/problem-message';
import { TextDiff } from '@/components/text-diff';
import { tr } from '@/i18n/tr';
import { API_PROBLEM_CODES, CLIENT_PROBLEM_CODES } from '@/lib/problem';
import { ApprovalStages, ReviewBadges } from '@/review/badges';
import { useFakeApi } from './fake-api';
import { reviewDetail, reviewItem } from './fixtures';
import { renderWithProviders } from './render-app';

describe('ProblemMessage', () => {
  it.each([...API_PROBLEM_CODES, ...CLIENT_PROBLEM_CODES])(
    'shows the Turkish message of %s',
    (kod) => {
      render(<ProblemMessage error={{ kod, status: 400 }} />);
      const alert = screen.getByRole('alert');
      expect(alert).toHaveAttribute('data-problem-code', kod);
      expect(within(alert).getByText(tr.problem.codes[kod])).toBeInTheDocument();
    },
  );

  it('shows a network failure as ag-hatasi', () => {
    render(<ProblemMessage error={new TypeError('Failed to fetch')} />);
    expect(screen.getByText(tr.problem.codes['ag-hatasi'])).toBeInTheDocument();
  });

  it('uses the wording of the operation', () => {
    render(<ProblemMessage error={{ kod: 'surum-uyusmazligi', status: 412 }} context="bulk" />);
    expect(screen.getByText(tr.problem.contexts.bulk['surum-uyusmazligi'])).toBeInTheDocument();
  });

  it('shows the offset message verbatim', () => {
    render(
      <ProblemMessage
        error={{
          kod: 'inceleme-desteklenmiyor',
          status: 422,
          detail: 'Ofsetli alanlar (marks, sentences) var.',
        }}
        context="decision"
      />,
    );
    expect(
      screen.getByText(
        "Bu birimin ofsetli alanları (işaretler, cümleler) var; metin düzeltmesi A16'da desteklenecek",
      ),
    ).toBeInTheDocument();
  });

  it('lists field errors, affected records, the open release, the anchor code and the trace id', () => {
    render(
      <ProblemMessage
        error={{
          kod: 'dogrulama',
          status: 400,
          detail: 'Gecersiz istek.',
          errors: { gerekce: ['gerekce alanı zorunludur.'] },
          kimlikler: [3, 5],
          kimlik: 7,
          yayin: {
            id: 42,
            surum: '1.0.0',
            derleme: 'internal',
            durum: 'hazirlaniyor',
            talep: 'yayin',
          },
          capa_hata_kodu: 'KANONIK_DEGIL',
          traceId: 'iz-123',
        }}
        releaseLink={(id) => <a href={`/yayinlar/${id}`}>{`Yayın ${id}`}</a>}
      />,
    );
    expect(screen.getByText('gerekce: gerekce alanı zorunludur.')).toBeInTheDocument();
    expect(screen.getByText(`${tr.problem.ids(2)}: 3, 5`)).toBeInTheDocument();
    expect(screen.getByText(tr.bulk.recordLabel(7))).toBeInTheDocument();
    expect(screen.getByText(`${tr.problem.anchorCode}: KANONIK_DEGIL`)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Yayın 42' })).toHaveAttribute('href', '/yayinlar/42');
    expect(screen.getByText(/42 internal hazirlaniyor/)).toBeInTheDocument();
    expect(
      screen.getByText(`${tr.problem.status(400)} · ${tr.problem.traceId}: iz-123`),
    ).toBeInTheDocument();
  });

  it('shows an unknown code raw', () => {
    render(<ProblemMessage error={{ kod: 'yeni-bir-kod', status: 418 }} />);
    expect(screen.getByText(tr.problem.unknownCode('yeni-bir-kod'))).toBeInTheDocument();
  });
});

describe('ArabicText', () => {
  it('sets lang, dir and the Quran font and renders the text exactly (no trim, no normalization)', () => {
    const text = '  \u0628\u064e\u0651\u00a0\u062a  ';
    render(<ArabicText text={text} data-testid="ar" />);
    const element = screen.getByTestId('ar');
    expect(element).toHaveAttribute('lang', 'ar');
    expect(element).toHaveAttribute('dir', 'rtl');
    expect(element).toHaveClass('font-quran');
    expect(element.textContent).toBe(text);
  });

  it('keeps decomposed and composed forms as they are', () => {
    render(<ArabicText text={'e\u0301'} data-testid="a" />);
    expect(screen.getByTestId('a').textContent).toBe('e\u0301');
  });

  it('renders as another element when asked', () => {
    render(<ArabicText as="p" text="x" data-testid="p" />);
    expect(screen.getByTestId('p').tagName).toBe('P');
  });
});

describe('OpenQuestionButton', () => {
  const fake = useFakeApi();

  it('carries the open question label, stays focusable and sends no request when clicked', async () => {
    const { user } = renderWithProviders(fake, <OpenQuestionButton label="Böl" phase="A16" />);
    const button = screen.getByRole('button', { name: `Böl · ${tr.openQuestion('A16')}` });
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toHaveTextContent('Açık soru: A16');
    await user.tab();
    expect(button).toHaveFocus();
    await user.click(button);
    await user.keyboard('{Enter}');
    expect(fake.calls).toHaveLength(0);
  });

  it.each(['A16', 'A17', 'A18'] as const)('names the stage %s', (phase) => {
    render(<OpenQuestionButton label="Eylem" phase={phase} />);
    expect(screen.getByRole('button')).toHaveTextContent(`Açık soru: ${phase}`);
  });
});

describe('MissingSection', () => {
  it('shows a heading and the note that the API does not have the data yet', () => {
    render(<MissingSection title="Kök, tür, sıklık" phase="A17/A18" />);
    expect(screen.getByRole('heading', { level: 3, name: 'Kök, tür, sıklık' })).toBeInTheDocument();
    expect(screen.getByText("Bu bilgi API'de henüz yok (A17/A18)")).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Kök, tür, sıklık' })).toBeInTheDocument();
  });
});

describe('badges', () => {
  it('draws "Doğrulanmamış" only from the dogrulanmamis field', () => {
    const { rerender } = render(<ReviewBadges review={reviewItem({ dogrulanmamis: true })} />);
    expect(screen.getByText(tr.badge.unverified)).toBeInTheDocument();
    // yz_modeli alone is not enough: the API's field decides.
    rerender(
      <ReviewBadges review={reviewItem({ dogrulanmamis: false, yz_modeli: 'deneme-model' })} />,
    );
    expect(screen.queryByText(tr.badge.unverified)).not.toBeInTheDocument();
    // And the field alone is enough without yz_modeli.
    rerender(<ReviewBadges review={reviewItem({ dogrulanmamis: true, yz_modeli: null })} />);
    expect(screen.getByText(tr.badge.unverified)).toBeInTheDocument();
  });

  it('shows "İkinci onay bekliyor" apart from the status', () => {
    render(<ReviewBadges review={reviewItem({ ikinci_onay_bekliyor: true, durum: 'acik' })} />);
    expect(screen.getByText(tr.labels.status.acik)).toBeInTheDocument();
    expect(screen.getByText(tr.badge.secondPending)).toBeInTheDocument();
  });

  it('shows no second-approval badge when none is pending, and an unknown status raw', () => {
    render(
      <ReviewBadges review={reviewItem({ ikinci_onay_bekliyor: false, durum: 'yeni_durum' })} />,
    );
    expect(screen.queryByText(tr.badge.secondPending)).not.toBeInTheDocument();
    expect(screen.getByText('yeni_durum')).toBeInTheDocument();
  });

  it('draws the first and the second approval as two separate groups', () => {
    const review = reviewDetail({
      ikinci_onay_bekliyor: true,
      inceleyen: 'birinci@deneme.test',
      incelendi_at: '2026-11-02T10:00:00Z',
      gerekce: 'Birinci gerekçe',
    });
    render(<ApprovalStages review={review} />);
    const first = screen.getByTestId('approval-first');
    const second = screen.getByTestId('approval-second');
    expect(first).toHaveTextContent('birinci@deneme.test');
    expect(first).toHaveTextContent('Birinci gerekçe');
    expect(second).toHaveTextContent(tr.approval.waiting);
    expect(second).not.toHaveTextContent('birinci@deneme.test');
    expect(first).not.toContainElement(second);
  });

  it('shows the second approver and reason once the second approval is given', () => {
    const review = reviewDetail({
      durum: 'onaylandi',
      inceleyen: 'birinci@deneme.test',
      ikinci_inceleyen: 'ikinci@deneme.test',
      ikinci_gerekce: 'İkinci gerekçe',
      ikinci_onay_bekliyor: false,
    });
    render(<ApprovalStages review={review} />);
    expect(screen.getByTestId('approval-first')).toHaveTextContent('birinci@deneme.test');
    expect(screen.getByTestId('approval-second')).toHaveTextContent('ikinci@deneme.test');
    expect(screen.getByTestId('approval-second')).toHaveTextContent('İkinci gerekçe');
  });

  it('shows only the first group for a single-stage record', () => {
    render(<ApprovalStages review={reviewDetail({ inceleyen: null })} />);
    expect(screen.getByTestId('approval-first')).toBeInTheDocument();
    expect(screen.queryByTestId('approval-second')).not.toBeInTheDocument();
  });
});

describe('TextDiff', () => {
  it('marks removed and added words', () => {
    render(<TextDiff before="Deneme paragrafı 1" after="Deneme paragrafı 2" />);
    const diff = screen.getByTestId('text-diff');
    expect(diff.querySelector('del')).toHaveTextContent('1');
    expect(diff.querySelector('ins')).toHaveTextContent('2');
    // Hidden group names sit around the marked words (see test/ui-fixes.test.tsx); the words themselves stay as given.
    expect(diff.textContent).toContain('Deneme paragrafı ');
  });

  it('renders Arabic with lang and dir', () => {
    render(<TextDiff arabic before={'\u0628\u064e'} after={'\u0628\u064f'} />);
    const diff = screen.getByTestId('text-diff');
    expect(diff).toHaveAttribute('lang', 'ar');
    expect(diff).toHaveAttribute('dir', 'rtl');
    expect(diff.querySelector('del')?.textContent).toBe('\u0628\u064e');
    expect(diff.querySelector('ins')?.textContent).toBe('\u0628\u064f');
  });
});
