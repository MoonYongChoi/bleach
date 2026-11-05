import type { Metadata } from "next";
import Link from "next/link";
import { InfoPage } from "@/components/info-page";
import { PLATFORMS } from "@/lib/campaigns";

export const metadata: Metadata = {
  title: "서비스 소개 — bleach",
  description: "여러 체험단 사이트의 모집 정보를 한곳에서 비교하는 bleach 소개",
};

export default function AboutPage() {
  return (
    <InfoPage title="서비스 소개">
      <section>
        <p>
          bleach는 여러 체험단 사이트에 흩어진 블로그·SNS 리뷰 체험단 모집 정보를 한곳에 모아, 조건에 맞는 체험단을
          빠르게 찾을 수 있게 돕는 서비스입니다.
        </p>
      </section>

      <section>
        <h2>모으는 곳</h2>
        <p>{PLATFORMS.join(", ")}의 공개된 모집 목록을 모읍니다. 체험단 신청과 선정, 리뷰 안내는 모두 각 사이트에서 이루어지며, bleach는 각 사이트와 제휴 관계가 아닙니다.</p>
      </section>

      <section>
        <h2>할 수 있는 일</h2>
        <ul>
          <li>방문 체험·제품 제공·구매 후 환급·기자단 같은 체험 방식으로 거르기</li>
          <li>시/도와 시/군/구 단위 지역, 카테고리, 리뷰 채널(블로그·릴스·쇼츠 등)로 거르기</li>
          <li>마감 임박순, 경쟁 낮은순, 모집인원 많은순으로 정렬하기</li>
          <li>관심 체험단을 별표로 모아 두기 (이 기기에만 저장)</li>
        </ul>
      </section>

      <section>
        <h2>경쟁률은 이렇게 계산합니다</h2>
        <p>
          경쟁률은 <b>신청 인원 ÷ 모집 인원</b>입니다. 예를 들어 10명을 뽑는데 32명이 신청했다면 3.2:1입니다. 신청이 모집보다
          적으면 &ldquo;여유&rdquo;로 표시합니다. 일부 사이트는 신청 인원 대신 대기 인원을 공개하므로 사이트마다 의미가 조금 다를 수
          있습니다.
        </p>
      </section>

      <section>
        <h2>정보 갱신</h2>
        <p>
          모집 정보는 하루 네 번(한국 시간 오전 3시 30분, 오전 9시 30분, 오후 3시 30분, 오후 9시 30분) 다시 모읍니다. 마감일이
          지났거나 원래 사이트에서 마감으로 확인된 체험단은 목록에서 내립니다. 신청 인원처럼 수시로 바뀌는 값은 실제와 차이가
          있을 수 있으니, 신청 전에는 원래 사이트에서 내용을 꼭 확인해 주세요.
        </p>
      </section>

      <section>
        <h2>사이트 추가 요청</h2>
        <p>
          모아 줬으면 하는 체험단 사이트가 있으면 <Link href="/">첫 화면</Link> 맨 아래의 &ldquo;추가 요청하기&rdquo;로 알려
          주세요.
        </p>
      </section>
    </InfoPage>
  );
}
