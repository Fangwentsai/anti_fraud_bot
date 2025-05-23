def create_donation_easter_egg_flex_message():
    """創建贊助彩蛋的特殊Flex Message - 當用戶分析我們的贊助網站時顯示"""
    try:
        donation_url = "https://buymeacoffee.com/todao_antifruad"
        logger.info(f"創建贊助彩蛋Flex Message，使用URL: {donation_url}")
        
        flex_message = FlexSendMessage(
            alt_text="恭喜你，這是我們的小彩蛋👑",
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "恭喜你，這是我們的小彩蛋👑",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#FF6B35",
                            "align": "center",
                            "wrap": True
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "🎉",
                                    "size": "xxl",
                                    "align": "center",
                                    "margin": "md"
                                },
                                {
                                    "type": "text",
                                    "text": "這個不是詐騙網站，這就是支持土豆(To-dao)的網站，希望大家能用小小心意幫忙鼓勵我，土豆會更有力氣提醒大家防詐騙啦！👏",
                                    "size": "md",
                                    "color": "#333333",
                                    "align": "center",
                                    "wrap": True,
                                    "margin": "lg"
                                }
                            ]
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "贊助我們",
                                "uri": donation_url
                            },
                            "color": "#FF8C42"
                        }
                    ]
                },
                "styles": {
                    "body": {
                        "backgroundColor": "#FFF8F0"
                    },
                    "footer": {
                        "backgroundColor": "#FFF8F0"
                    }
                }
            }
        )
        
        logger.info("贊助彩蛋Flex Message創建成功")
        return flex_message
        
    except Exception as e:
        logger.error(f"創建贊助彩蛋Flex Message時發生錯誤: {e}")
        # 如果創建失敗，返回簡單的文字訊息
        return TextSendMessage(text="恭喜你，這是我們的小彩蛋👑\n\n這個不是詐騙網站，這就是支持土豆(To-dao)的網站，希望大家能用小小心意幫忙鼓勵我，土豆會更有力氣提醒大家防詐騙啦！👏\n\n贊助連結：https://buymeacoffee.com/todao_antifruad") 