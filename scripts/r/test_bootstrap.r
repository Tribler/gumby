library(ggplot2)
library(reshape)

walk_rtts <- read.table("walk_rtts.txt", header=T, quote="\"")
walk_rtts$label <- factor(paste(walk_rtts$HOST_NAME, "(", walk_rtts$ADDRESS, ")", sep=''))
p <- ggplot(walk_rtts, aes(label, RTT))
p <- p + geom_boxplot(aes(fill=label))
p <- p + coord_flip()
p <- p + labs(title="Bootstrap server response time", 
              x="Server address", 
              y="Round-trip time (seconds)",
              colour="Server hostname")
p
ggsave("walk_rtts.png", width=10, height=6, dpi=100)

summary <- read.table("summary.txt", header=T, quote="\"")
summary$label <- factor(paste(summary$HOST_NAME, "(", summary$ADDRESS, ")", sep=''))
p <- ggplot(summary, aes(label, RESPONSES))
p <- p + geom_bar(aes(fill=label))
p <- p + coord_flip()
p <- p + ylim(0, max(summary$REQUESTS))
p <- p + labs(title=paste("Bootstrap server walk request success\nout of", max(summary$REQUESTS), "requests"),
              x="Server address",
              y="Successfull walks",
              colour="Server hostname")
p
ggsave("summary.png", width=10, height=6, dpi=100)

q(save="no")
