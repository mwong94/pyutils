use role extractor_role;

use warehouse loading;
use database raw_prod;
use schema raw_prod.apple_news;

-- drop table raw_prod.apple_news.channel_summary;
copy into raw_prod.apple_news.channel_summary
from (
    select
        $1 as channel,
        $2 as date,
        $3 as total_views,
        $4 as unique_viewers,
        $5 as article_shares,
        $6 as article_shares_by_messages,
        $7 as article_shares_by_mail,
        $8 as article_shares_by_twitter,
        $9 as article_shares_by_facebook,
        $10 as avg_active_time_seconds,
        $11 as likes,
        $12 as new_favorites,
        $13 as wau,
        $14 as mau,
        $15 as saves,
        $16 as removed_favorites,
        $17 as video_views,
        $18 as video_median_view_time_seconds,
        $19 as total_video_minutes_viewed,
        $20 as video_completion_rate,
        $21 as reach,
        $22 as demographics_proportion_male,
        $23 as demographics_proportion_female,
        $24 as demographics_proportion_age_18_24,
        $25 as demographics_proportion_age_25_34,
        $26 as demographics_proportion_age_35_44,
        $27 as demographics_proportion_age_45_54,
        $28 as demographics_proportion_age_55_64,
        $29 as demographics_proportion_age_65_plus,
        $30 as articles_featured_by_apple,
        METADATA$FILENAME as filename,
        current_timestamp as imported_at
    from @util.public.s3_prod_stage
        ( file_format => 'util.public.default_csv_format'
            , pattern => '.*apple_news/ChannelSummary/upload/.*ChannelSummary.csv'
--                , pattern => '.*apple_news/ChannelSummary/upload/20250901_20250930_ChannelSummary.csv'
        )
    as t
);
