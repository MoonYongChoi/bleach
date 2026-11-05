import type { Metadata } from "next";
import Link from "next/link";
import { InfoPage } from "@/components/info-page";
import { CONTACT_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "개인정보처리방침 — bleach",
  description: "bleach가 처리하는 정보와 광고 쿠키 안내",
};

// 실제 동작(코드) 기준으로 쓴 초안이다. 동작이 바뀌면(로그인, 이벤트 수집 등) 이 페이지도 함께 고친다.
export default function PrivacyPage() {
  return (
    <InfoPage title="개인정보처리방침" updated="시행일 2026년 11월 5일">
      <section>
        <p>
          bleach(이하 &ldquo;서비스&rdquo;)는 이용자의 개인정보를 소중히 다루며, 서비스를 운영하는 데 필요한 최소한의 정보만
          처리합니다. 서비스는 회원가입이나 로그인을 받지 않습니다.
        </p>
      </section>

      <section>
        <h2>1. 처리하는 정보와 목적</h2>
        <ul>
          <li>
            <b>사이트 추가 요청</b>: 이용자가 직접 입력한 사이트 이름, 사이트 주소, 메모, 그리고 회신을 원할 때 선택적으로
            입력한 이메일 주소. 요청을 검토하고 회신하는 데만 씁니다.
          </li>
          <li>
            <b>관심 체험단(별표)</b>: 이용자 기기의 브라우저 저장소에만 저장되며 서비스 서버로 보내지 않습니다. 브라우저 데이터를
            지우면 함께 지워집니다.
          </li>
          <li>
            <b>접속 기록</b>: 서비스를 제공하는 과정에서 호스팅 업체의 서버에 IP 주소, 브라우저 정보, 접속 시각 같은 기록이
            자동으로 남을 수 있습니다. 서비스 운영과 보안 목적으로만 쓰입니다.
          </li>
        </ul>
      </section>

      <section>
        <h2>2. 광고와 쿠키</h2>
        <p>
          서비스는 Google 애드센스 광고를 게재합니다. Google을 비롯한 제3자 광고 업체는 쿠키를 사용해 이용자가 이 서비스와 다른
          웹사이트를 방문한 기록을 바탕으로 광고를 보여 줄 수 있습니다. Google이 광고 쿠키를 사용하는 방식은{" "}
          <a href="https://policies.google.com/technologies/ads?hl=ko" target="_blank" rel="noopener noreferrer">
            Google 광고 정책
          </a>
          에서 확인할 수 있습니다.
        </p>
        <p className="mt-2">
          맞춤 광고를 원하지 않으면{" "}
          <a href="https://adssettings.google.com" target="_blank" rel="noopener noreferrer">
            Google 광고 설정
          </a>
          에서 끌 수 있고, 브라우저 설정에서 쿠키를 차단할 수도 있습니다.
        </p>
      </section>

      <section>
        <h2>3. 처리를 맡기는 업체</h2>
        <ul>
          <li>Supabase: 데이터베이스 (사이트 추가 요청 내용 저장)</li>
          <li>Vercel: 웹사이트 호스팅</li>
          <li>Resend: 사이트 추가 요청이 들어왔을 때 운영자에게 알림 메일 발송</li>
          <li>Google: 광고 게재</li>
        </ul>
        <p className="mt-2">이 업체들은 해외에 서버를 두고 있을 수 있습니다.</p>
      </section>

      <section>
        <h2>4. 보관 기간과 파기</h2>
        <p>
          사이트 추가 요청 정보는 요청을 검토하고 처리하는 동안 보관하며, 이용자가 삭제를 요청하면 지체 없이 삭제합니다.
        </p>
      </section>

      <section>
        <h2>5. 이용자의 권리</h2>
        <p>이용자는 자신이 보낸 정보의 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다. 아래 문의처로 연락해 주세요.</p>
      </section>

      <section>
        <h2>6. 문의처</h2>
        <p>
          {CONTACT_EMAIL ? (
            <>
              개인정보 관련 문의: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
            </>
          ) : (
            <>
              개인정보 관련 문의는 <Link href="/contact">문의 페이지</Link>를 참고해 주세요.
            </>
          )}
        </p>
      </section>

      <section>
        <h2>7. 변경</h2>
        <p>이 방침이 바뀌면 이 페이지에 시행일과 함께 알립니다.</p>
      </section>
    </InfoPage>
  );
}
