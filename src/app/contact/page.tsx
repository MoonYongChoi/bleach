import type { Metadata } from "next";
import Link from "next/link";
import { InfoPage } from "@/components/info-page";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "문의 — bleach",
  description: "bleach 운영자에게 문의하는 방법",
};

export default function ContactPage() {
  return (
    <InfoPage title="문의">
      <section>
        <h2>운영자에게 문의</h2>
        {CONTACT_EMAIL ? (
          <p>
            서비스 이용, 정보 오류 신고, 개인정보 관련 요청은 <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>로
            보내 주세요.
          </p>
        ) : (
          <p>문의 메일 주소를 준비하고 있습니다. 그동안은 아래 &ldquo;사이트 추가 요청&rdquo;으로 남겨 주세요.</p>
        )}
      </section>

      <section>
        <h2>체험단 신청·선정 문의</h2>
        <p>
          bleach는 모집 정보를 모아 보여 줄 뿐, 체험단 신청과 선정은 각 체험단 사이트에서 이루어집니다. 신청 내역, 선정 결과,
          리뷰 안내에 대한 문의는 해당 체험단 사이트로 해 주세요.
        </p>
      </section>

      <section>
        <h2>사이트 추가 요청</h2>
        <p>
          새 체험단 사이트를 추가해 달라는 요청은 <Link href="/">첫 화면</Link> 맨 아래 &ldquo;추가 요청하기&rdquo;에서 보낼 수
          있습니다.
        </p>
      </section>
    </InfoPage>
  );
}
